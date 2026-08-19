"""
F2T2EA stage transition rules for a FusedTrack.

Find    -> single-source, unconfirmed
Fix     -> 2+ independent sources corroborate the same track
Track   -> track has persisted across enough update cycles
Target  -> classification confidence/severity crosses the target threshold
Engage  -> requires explicit operator acknowledgement (see /tracks/{id}/ack)
Assess  -> terminal stage; track has gone stale after being engaged, or the
           operator explicitly closes it out

Engage is intentionally the one stage this system will NEVER set on its
own — it always requires an explicit human action via the API. Assess is
likewise about closing out a record, not taking any real-world effect.
"""

from backend.app.classification.detector import classify
from backend.app.models.schemas import F2T2EAStage, FusedTrack, ThreatSeverity

MIN_READINGS_FOR_TRACK = 3
TARGET_SEVERITIES = {ThreatSeverity.MEDIUM, ThreatSeverity.HIGH}


def advance_stage(track: FusedTrack) -> FusedTrack:
    track.severity = classify(track)

    next_stage = track.stage

    if track.stage == F2T2EAStage.FIND and len(set(track.contributing_sources)) >= 2:
        next_stage = F2T2EAStage.FIX

    elif track.stage == F2T2EAStage.FIX and track.reading_count >= MIN_READINGS_FOR_TRACK:
        next_stage = F2T2EAStage.TRACK

    elif track.stage == F2T2EAStage.TRACK and track.severity in TARGET_SEVERITIES:
        next_stage = F2T2EAStage.TARGET

    # ENGAGE is set only via acknowledge_track() below, never automatically.

    if next_stage != track.stage:
        track.stage = next_stage
        track.stage_history.append(next_stage)

    return track


def acknowledge_track(track: FusedTrack) -> FusedTrack:
    """Explicit operator action — the only path into ENGAGE."""
    if track.stage != F2T2EAStage.TARGET:
        raise ValueError(f"Track {track.track_id} is not in TARGET stage (currently {track.stage}).")

    track.operator_ack = True
    track.stage = F2T2EAStage.ENGAGE
    track.stage_history.append(F2T2EAStage.ENGAGE)
    return track


def assess_track(track: FusedTrack, summary: str = "") -> FusedTrack:
    """Explicit operator action to close out a track with an outcome note."""
    track.stage = F2T2EAStage.ASSESS
    track.stage_history.append(F2T2EAStage.ASSESS)
    return track
