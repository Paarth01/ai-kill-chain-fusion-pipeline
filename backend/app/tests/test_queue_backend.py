import pytest

from backend.app.fusion.queue_backend import InMemoryQueueBackend
from backend.app.models.schemas import Coordinates, SensorReading, SourceType


@pytest.mark.asyncio
async def test_in_memory_backend_put_and_get_round_trip():
    backend = InMemoryQueueBackend()
    reading = SensorReading(
        source_type=SourceType.VEHICLE_IR,
        entity_hint="test_entity",
        coordinates=Coordinates(lat=28.6, lon=77.2),
        confidence=0.7,
    )

    await backend.put(reading)
    result = await backend.get()

    assert result.reading_id == reading.reading_id
    assert result.source_type == SourceType.VEHICLE_IR


@pytest.mark.asyncio
async def test_in_memory_backend_preserves_order():
    backend = InMemoryQueueBackend()
    readings = [
        SensorReading(
            source_type=SourceType.ELINT,
            entity_hint=f"entity_{i}",
            coordinates=Coordinates(lat=28.6, lon=77.2),
            confidence=0.5,
        )
        for i in range(3)
    ]

    for r in readings:
        await backend.put(r)

    results = [await backend.get() for _ in range(3)]

    assert [r.entity_hint for r in results] == [f"entity_{i}" for i in range(3)]
