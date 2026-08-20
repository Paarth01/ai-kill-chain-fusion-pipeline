from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from backend.app.persistence.db import HistoryStore, resolve_database_url


@pytest_asyncio.fixture
async def store(tmp_path):
    """A real SQLite database on disk, isolated per test — not mocked,
    not shared with the app's own history_store singleton."""
    db_path = tmp_path / "test_history.db"
    s = HistoryStore(f"sqlite:///{db_path}")
    await s.init_db()
    yield s
    await s.dispose()


def test_resolve_database_url_adds_async_drivers():
    assert resolve_database_url("sqlite:///./x.db") == "sqlite+aiosqlite:///./x.db"
    assert resolve_database_url("postgres://u:p@host/db") == "postgresql+asyncpg://u:p@host/db"
    assert resolve_database_url("postgresql://u:p@host/db") == "postgresql+asyncpg://u:p@host/db"
    # Already-async URLs pass through unchanged.
    assert resolve_database_url("sqlite+aiosqlite:///./x.db") == "sqlite+aiosqlite:///./x.db"


@pytest.mark.asyncio
async def test_log_and_retrieve_single_track_history(store):
    t0 = datetime.utcnow()
    await store.log_stage_event("TRK-001", "find", "unknown", 0.5, ["vehicle_ir"], t0)
    await store.log_stage_event(
        "TRK-001", "fix", "low", 0.65, ["vehicle_ir", "uav_uas"], t0 + timedelta(seconds=10)
    )

    history = await store.get_track_history("TRK-001")

    assert len(history) == 2
    assert history[0]["stage"] == "find"
    assert history[1]["stage"] == "fix"
    assert history[1]["contributing_sources"] == ["vehicle_ir", "uav_uas"]


@pytest.mark.asyncio
async def test_history_is_ordered_by_timestamp_not_insertion_order(store):
    t0 = datetime.utcnow()
    # Insert out of chronological order on purpose.
    await store.log_stage_event("TRK-002", "fix", "low", 0.6, ["uav_uas"], t0 + timedelta(seconds=10))
    await store.log_stage_event("TRK-002", "find", "unknown", 0.4, ["uav_uas"], t0)

    history = await store.get_track_history("TRK-002")

    assert [h["stage"] for h in history] == ["find", "fix"]


@pytest.mark.asyncio
async def test_get_track_history_only_returns_that_track(store):
    t0 = datetime.utcnow()
    await store.log_stage_event("TRK-A", "find", "unknown", 0.5, ["elint"], t0)
    await store.log_stage_event("TRK-B", "find", "unknown", 0.5, ["elint"], t0)

    history_a = await store.get_track_history("TRK-A")

    assert len(history_a) == 1
    assert history_a[0]["track_id"] == "TRK-A"


@pytest.mark.asyncio
async def test_get_recent_history_respects_limit_and_recency_order(store):
    t0 = datetime.utcnow()
    for i in range(5):
        await store.log_stage_event(f"TRK-{i}", "find", "unknown", 0.5, ["elint"], t0 + timedelta(seconds=i))

    recent = await store.get_recent_history(limit=3)

    assert len(recent) == 3
    # Most recent first.
    assert recent[0]["track_id"] == "TRK-4"
    assert recent[1]["track_id"] == "TRK-3"
    assert recent[2]["track_id"] == "TRK-2"


@pytest.mark.asyncio
async def test_history_persists_across_store_instances_against_the_same_file(tmp_path):
    """Confirms this is genuinely durable — a new HistoryStore pointed at
    the same file sees data written by a previous instance, unlike the
    in-memory FusionEngine which loses everything on restart."""
    db_path = tmp_path / "durable.db"

    store1 = HistoryStore(f"sqlite:///{db_path}")
    await store1.init_db()
    await store1.log_stage_event("TRK-DURABLE", "find", "unknown", 0.5, ["elint"], datetime.utcnow())
    await store1.dispose()

    store2 = HistoryStore(f"sqlite:///{db_path}")
    history = await store2.get_track_history("TRK-DURABLE")
    await store2.dispose()

    assert len(history) == 1
    assert history[0]["track_id"] == "TRK-DURABLE"
