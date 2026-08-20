"""
Confirms HistoryStore's Postgres path actually works against a real
PostgreSQL instance — not just SQLite (test_persistence.py) plus an
assumption that SQLAlchemy's portability claim holds. It's a reasonable
assumption, but this project's standard throughout has been "run it, don't
assume it" — this closes that specific gap.

Skips cleanly if Postgres isn't reachable, same pattern as
test_redis_queue_correctness.py for its optional dependency.

Setup used to verify this locally:
    apt-get install -y postgresql
    service postgresql start
    su postgres -c "psql -c \"ALTER USER postgres PASSWORD 'testpass';\""
    su postgres -c "psql -c \"CREATE DATABASE sentinel_test;\""
"""

from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from backend.app.persistence.db import HistoryStore, resolve_database_url

POSTGRES_URL = "postgres://postgres:testpass@localhost:5432/sentinel_test"


def _postgres_reachable() -> bool:
    import asyncio

    async def _try_connect():
        import asyncpg

        conn = await asyncpg.connect(
            host="localhost", port=5432, user="postgres", password="testpass", database="sentinel_test", timeout=2
        )
        await conn.close()

    try:
        asyncio.run(_try_connect())
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_reachable(), reason="Postgres not reachable at localhost:5432/sentinel_test"
)


@pytest_asyncio.fixture
async def store():
    s = HistoryStore(POSTGRES_URL)
    await s.init_db()
    yield s
    # Clean up this test's rows rather than dropping the table, so
    # concurrent test runs against the same database don't race on DDL.
    from sqlalchemy import text

    async with s._engine.begin() as conn:
        await conn.execute(text("DELETE FROM stage_events WHERE track_id LIKE 'TRK-PGTEST-%'"))
    await s.dispose()


def test_resolve_database_url_normalizes_both_postgres_url_forms():
    assert resolve_database_url(POSTGRES_URL) == "postgresql+asyncpg://postgres:testpass@localhost:5432/sentinel_test"
    assert (
        resolve_database_url("postgresql://postgres:testpass@localhost:5432/sentinel_test")
        == "postgresql+asyncpg://postgres:testpass@localhost:5432/sentinel_test"
    )


@pytest.mark.asyncio
async def test_init_db_creates_table_against_real_postgres(store):
    # If init_db() (called in the fixture) didn't actually succeed against
    # real Postgres, logging an event below would raise — this is an
    # end-to-end check, not just "the function returned without an
    # exception in isolation."
    await store.log_stage_event("TRK-PGTEST-001", "find", "unknown", 0.5, ["vehicle_ir"], datetime.utcnow())
    history = await store.get_track_history("TRK-PGTEST-001")
    assert len(history) == 1


@pytest.mark.asyncio
async def test_log_and_retrieve_history_against_real_postgres(store):
    t0 = datetime.utcnow()
    await store.log_stage_event("TRK-PGTEST-002", "find", "unknown", 0.5, ["elint"], t0)
    await store.log_stage_event(
        "TRK-PGTEST-002", "fix", "low", 0.65, ["elint", "uav_uas"], t0 + timedelta(seconds=10)
    )

    history = await store.get_track_history("TRK-PGTEST-002")

    assert len(history) == 2
    assert history[0]["stage"] == "find"
    assert history[1]["stage"] == "fix"
    assert history[1]["contributing_sources"] == ["elint", "uav_uas"]


@pytest.mark.asyncio
async def test_data_persists_across_store_instances_against_real_postgres():
    """The same durability claim as SQLite's equivalent test, but against
    a real network database rather than a local file — confirms this
    isn't relying on any SQLite-specific behavior."""
    store1 = HistoryStore(POSTGRES_URL)
    await store1.init_db()
    await store1.log_stage_event("TRK-PGTEST-003", "find", "unknown", 0.5, ["legacy_c2"], datetime.utcnow())
    await store1.dispose()

    store2 = HistoryStore(POSTGRES_URL)
    history = await store2.get_track_history("TRK-PGTEST-003")

    from sqlalchemy import text

    async with store2._engine.begin() as conn:
        await conn.execute(text("DELETE FROM stage_events WHERE track_id = 'TRK-PGTEST-003'"))
    await store2.dispose()

    assert len(history) == 1
    assert history[0]["track_id"] == "TRK-PGTEST-003"


@pytest.mark.asyncio
async def test_get_recent_history_ordering_against_real_postgres(store):
    t0 = datetime.utcnow()
    for i in range(3):
        await store.log_stage_event(
            f"TRK-PGTEST-recent-{i}", "find", "unknown", 0.5, ["elint"], t0 + timedelta(seconds=i)
        )

    recent = await store.get_recent_history(limit=3)

    assert [r["track_id"] for r in recent] == [
        "TRK-PGTEST-recent-2",
        "TRK-PGTEST-recent-1",
        "TRK-PGTEST-recent-0",
    ]
