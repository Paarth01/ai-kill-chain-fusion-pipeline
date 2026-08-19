"""
Core fusion logic: matches incoming SensorReadings to existing FusedTracks
by spatial proximity + recency, merging corroborating readings into a
single track and boosting confidence when multiple independent source
types agree. Unmatched readings spawn a new track.

This is intentionally simple (nearest-neighbor + threshold) rather than a
full Kalman-filter/JPDA implementation — the point of this scaffold is to
demonstrate the fusion *architecture* and the F2T2EA progression it feeds,
not to ship a production-grade tracker.
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

            distance = _haversine_km(reading.coordinates, track.coordinates)
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
        track.coordinates = Coordinates(
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
