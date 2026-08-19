"""
Assigns a ThreatSeverity to a FusedTrack based on its accumulated
confidence and how many independent sources corroborate it.

--- Where the real model plugs in later ---
Swap `classify()` for a call into the YOLOv8n + ByteTrack pipeline from the
Purplle Tech Challenge project: instead of deriving severity from fusion
confidence alone, run inference on the vehicle/IR feed's actual frame data
and combine the model's class/confidence output with the multi-source
corroboration signal already computed here. The FusedTrack shape doesn't
need to change — just how `severity` gets set.
"""

from backend.app.models.schemas import FusedTrack, ThreatSeverity


def classify(track: FusedTrack) -> ThreatSeverity:
    corroboration = len(set(track.contributing_sources))

    if track.confidence >= 0.8 and corroboration >= 3:
        return ThreatSeverity.HIGH
    if track.confidence >= 0.6 and corroboration >= 2:
        return ThreatSeverity.MEDIUM
    if track.confidence >= 0.4:
        return ThreatSeverity.LOW
    return ThreatSeverity.UNKNOWN
