"""
Core data contracts for Sentinel-FFT2EA.

Every synthetic sensor reading normalizes into a `SensorReading` before it
reaches the fusion engine. Fused entities live as `FusedTrack` objects and
carry an F2T2EA `stage` that advances as more corroborating evidence and
classification confidence accumulate.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    VEHICLE_IR = "vehicle_ir"
    UAV_UAS = "uav_uas"
    ELINT = "elint"
    LEGACY_C2 = "legacy_c2"
    HUMINT = "humint"


class ThreatSeverity(str, Enum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class F2T2EAStage(str, Enum):
    FIND = "find"        # single-source detection, unconfirmed
    FIX = "fix"           # 2+ corroborating sources, position confirmed
    TRACK = "track"        # persists across multiple update cycles
    TARGET = "target"       # classified with sufficient confidence/severity
    ENGAGE = "engage"       # operator has acknowledged/confirmed the track
    ASSESS = "assess"       # track archived with an outcome summary


class Coordinates(BaseModel):
    lat: float
    lon: float


class HumintConfidence(str, Enum):
    """Human sources report a qualitative confidence band, not a number —
    an informant says "fairly sure", not "0.62". Mapped to the numeric
    scale SensorReading needs by HUMINT_CONFIDENCE_SCORES below."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Rule-based band -> score. Deliberately not NLP: the reporting officer's
# own stated confidence is better evidence than anything inferred from the
# report's prose would be.
HUMINT_CONFIDENCE_SCORES: dict[HumintConfidence, float] = {
    HumintConfidence.LOW: 0.25,
    HumintConfidence.MEDIUM: 0.55,
    HumintConfidence.HIGH: 0.8,
}


class HumintReport(BaseModel):
    """Wire format for a human intelligence report, POSTed to
    /ingest/humint. Unlike the four sensor feeds, HUMINT is push-based —
    a person files a report when they have something, so there's no
    polling interval and no BaseFeed subclass for it.

    `location` is required with no default: a report that can't be placed
    on the map can't be fused (fusion matches on position), so it's
    rejected at the schema boundary rather than silently defaulted to
    coordinates nobody observed.
    """

    source_id: str
    report_text: str
    location: Coordinates
    confidence: HumintConfidence
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SensorReading(BaseModel):
    """Normalized shape every feed adapter must produce before it hits the
    fusion queue, regardless of the feed's native wire format."""

    reading_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    source_type: SourceType
    entity_hint: str  # feed's own best-guess label for what it's seeing
    coordinates: Coordinates
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    degraded: bool = False  # set True when the EW simulator has corrupted it
    raw_signature: Optional[str] = None  # e.g. ELINT RF signature string


class FusedTrack(BaseModel):
    """A single fused entity built from one or more corroborating readings."""

    track_id: str = Field(default_factory=lambda: f"TRK-{uuid4().hex[:8].upper()}")
    coordinates: Coordinates
    contributing_sources: list[SourceType] = Field(default_factory=list)
    reading_count: int = 1
    confidence: float = Field(ge=0.0, le=1.0, default=0.3)
    severity: ThreatSeverity = ThreatSeverity.UNKNOWN
    stage: F2T2EAStage = F2T2EAStage.FIND
    stage_history: list[F2T2EAStage] = Field(default_factory=lambda: [F2T2EAStage.FIND])
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    operator_ack: bool = False
    degraded: bool = False

    # Constant-velocity estimate (degrees/second), used by the fusion
    # engine to predict where a moving track should be at the next
    # update rather than matching against its last-known position — see
    # fusion/fusion_engine.py's predict_position(). This is NOT full
    # multi-hypothesis tracking (JPDA) — no competing hypotheses are
    # maintained, just a single predicted position per track — named
    # accordingly rather than oversold.
    velocity_lat: float = 0.0
    velocity_lon: float = 0.0

    class Config:
        use_enum_values = False
