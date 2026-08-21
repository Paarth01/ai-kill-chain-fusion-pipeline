"""
HUMINT ingestion adapter.

The other four sources are `BaseFeed` subclasses: background producers that
generate a reading on a timer. HUMINT deliberately isn't one — a human files
a report when they have something to report, so it arrives by POST to
/ingest/humint rather than on an interval. What it shares with the other
four is the part that matters: it normalizes into the same `SensorReading`
before touching the fusion queue, so fusion, the state machine, persistence,
and the dashboard need no HUMINT-specific handling.

Extraction is rule-based, not NLP: the reporting officer's stated confidence
band maps to a score, and the reported location maps straight through. Making
a language model second-guess a human's own stated confidence would be worse
evidence, not better — and `report_text` is preserved verbatim in
`raw_signature` so the operator reads the actual words rather than a
lossy machine summary of them.
"""

from __future__ import annotations

from backend.app.models.schemas import (
    HUMINT_CONFIDENCE_SCORES,
    HumintReport,
    SensorReading,
    SourceType,
)


def build_contact_from_humint(report: HumintReport) -> SensorReading:
    """Maps a HumintReport onto the shared internal SensorReading schema.

    Note `degraded` is left False: EW jamming models RF interference against
    a sensor, and a written human report isn't subject to it the same way —
    see EW_APPLICABLE_SOURCES in ew/ew_simulator.py.
    """
    return SensorReading(
        source_type=SourceType.HUMINT,
        entity_hint="human_report",
        coordinates=report.location,
        confidence=HUMINT_CONFIDENCE_SCORES[report.confidence],
        timestamp=report.timestamp,
        # Kept verbatim so the operator sees the reporter's own words, and
        # prefixed with source_id for attribution/traceability back to who
        # filed it — the ELINT feed uses this same field for RF signatures.
        raw_signature=f"{report.source_id}: {report.report_text}",
    )
