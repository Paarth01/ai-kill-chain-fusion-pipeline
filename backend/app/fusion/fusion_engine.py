"""
Core fusion logic: matches incoming SensorReadings to existing FusedTracks
by spatial proximity + recency, merging corroborating readings into a
single track and boosting confidence when multiple independent source
types agree. Unmatched readings spawn a new track.

Matching uses a predicted position (predict_position()) — a constant-
velocity estimate extrapolated from the track's last two updates — rather
than just the track's last-known position. This meaningfully improves
matching for a moving target: a fast-moving track whose next reading
lands outside the raw distance threshold from its *last* position can
still match correctly if that position was predictable from its recent
heading. This is explicitly NOT full multi-hypothesis tracking (JPDA) —
there's a single predicted position per track, not a maintained set of
competing hypotheses — named and scoped honestly rather than oversold.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from backend.app.config import settings
from backend.app.models.schemas import Coordinates, FusedTrack, SensorReading


def _haversine_km(a: Coordinates, b: Coordinates) -> float:
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [a.lat, a.lon, b.lat, b.lon])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def predict_position(track: FusedTrack, at_time: datetime) -> Coordinates:
    """Extrapolates the track's position at `at_time` using its current
    constant-velocity estimate (degrees/second). With zero velocity (a
    brand-new track, or one that hasn't moved) this is just the track's
    current position — the prediction gracefully degrades to the old
    behavior rather than needing a special case."""
    dt = (at_time - track.last_updated).total_seconds()
    return Coordinates(
        lat=track.coordinates.lat + track.velocity_lat * dt,
        lon=track.coordinates.lon + track.velocity_lon * dt,
    )


def _update_velocity(track: FusedTrack, new_position: Coordinates, new_time: datetime) -> tuple[float, float]:
    """Simple two-point velocity estimate (degrees/second) between the
    track's pre-update position and its new merged position. Smoothed
    against the previous velocity estimate (70% new / 30% old) rather
    than replaced outright, so one noisy reading doesn't swing the
    heading estimate wildly."""
    dt = (new_time - track.last_updated).total_seconds()
    if dt <= 0:
        return track.velocity_lat, track.velocity_lon

    raw_v_lat = (new_position.lat - track.coordinates.lat) / dt
    raw_v_lon = (new_position.lon - track.coordinates.lon) / dt

    smoothed_v_lat = 0.7 * raw_v_lat + 0.3 * track.velocity_lat
    smoothed_v_lon = 0.7 * raw_v_lon + 0.3 * track.velocity_lon
    return smoothed_v_lat, smoothed_v_lon


class FusionEngine:
    def __init__(self):
        self.tracks: dict[str, FusedTrack] = {}

    def ingest(self, reading: SensorReading) -> FusedTrack:
        match = self._find_match(reading)
        if match:
            return self._merge(match, reading)
        return self._create_track(reading)

    def _find_match(self, reading: SensorReading) -> FusedTrack | None:
        best_match, best_distance = None, None
        for track in self.tracks.values():
            time_gap = abs((reading.timestamp - track.last_updated).total_seconds())
            if time_gap > settings.FUSION_TIME_WINDOW_SECONDS:
                continue

            predicted = predict_position(track, reading.timestamp)
            distance = _haversine_km(reading.coordinates, predicted)
            if distance > settings.FUSION_DISTANCE_THRESHOLD_KM:
                continue

            if best_distance is None or distance < best_distance:
                best_match, best_distance = track, distance

        return best_match

    def _create_track(self, reading: SensorReading) -> FusedTrack:
        track = FusedTrack(
            coordinates=reading.coordinates,
            contributing_sources=[reading.source_type],
            confidence=reading.confidence,
            last_updated=reading.timestamp,
            first_seen=reading.timestamp,
            degraded=reading.degraded,
        )
        self.tracks[track.track_id] = track
        return track

    def _merge(self, track: FusedTrack, reading: SensorReading) -> FusedTrack:
        # Weighted-average position by confidence.
        total_weight = track.confidence + reading.confidence
        new_position = Coordinates(
            lat=round(
                (track.coordinates.lat * track.confidence + reading.coordinates.lat * reading.confidence)
                / total_weight,
                5,
            ),
            lon=round(
                (track.coordinates.lon * track.confidence + reading.coordinates.lon * reading.confidence)
                / total_weight,
                5,
            ),
        )

        track.velocity_lat, track.velocity_lon = _update_velocity(track, new_position, reading.timestamp)
        track.coordinates = new_position

        is_new_source = reading.source_type not in track.contributing_sources
        if is_new_source:
            track.contributing_sources.append(reading.source_type)

        # Corroboration from an independent source type is worth more than
        # another reading from a source already contributing.
        bump = 0.15 if is_new_source else 0.05
        track.confidence = min(1.0, round(track.confidence + bump, 2))

        track.reading_count += 1
        track.last_updated = reading.timestamp
        track.degraded = track.degraded or reading.degraded

        return track

    def prune_stale(self, now: datetime | None = None) -> list[str]:
        """Remove tracks that haven't been updated recently. Returns removed IDs."""
        now = now or datetime.utcnow()
        stale_ids = [
            tid
            for tid, t in self.tracks.items()
            if (now - t.last_updated) > timedelta(seconds=settings.TRACK_STALE_AFTER_SECONDS)
        ]
        for tid in stale_ids:
            del self.tracks[tid]
        return stale_ids

    def snapshot(self) -> list[FusedTrack]:
        return list(self.tracks.values())


# Module-level singleton for the scaffold's single-process design.
fusion_engine = FusionEngine()
