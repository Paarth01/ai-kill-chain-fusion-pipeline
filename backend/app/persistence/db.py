"""
Stage-event history log: every time a FusedTrack's F2T2EA stage changes,
a row is written here. Answers "what happened and when" after the fact —
the in-memory FusionEngine loses everything on restart, this doesn't.

Backend is SQLite by default (a local file, zero setup) and switches to
Postgres automatically if DATABASE_URL is set to a postgres:// URL —
SQLAlchemy's async engine makes both work through the same code path, the
same pattern as fusion/queue_backend.py's in-memory/Redis split.

Structured as a class (HistoryStore) rather than module-level globals so
tests can construct an isolated instance against a temp-file SQLite
database instead of fighting the app's shared instance — the same
testability reasoning as FusionEngine and EWSimulator being classes
rather than module-level dicts/sets.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from backend.app.config import settings


class Base(DeclarativeBase):
    pass


class StageEvent(Base):
    __tablename__ = "stage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[str] = mapped_column(String(32), index=True)
    stage: Mapped[str] = mapped_column(String(16))
    severity: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    contributing_sources: Mapped[str] = mapped_column(String(128))  # comma-joined, kept simple
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)


def resolve_database_url(raw_url: str) -> str:
    """Normalizes a plain postgres:// / sqlite:// URL (what a person would
    naturally set) into the async-driver form SQLAlchemy needs: asyncpg
    for Postgres, aiosqlite for SQLite."""
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
    if raw_url.startswith("postgresql://") and "+asyncpg" not in raw_url:
        return raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if raw_url.startswith("sqlite://") and "+aiosqlite" not in raw_url:
        return raw_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return raw_url


class HistoryStore:
    def __init__(self, database_url: str):
        self._engine = create_async_engine(resolve_database_url(database_url))
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    async def init_db(self) -> None:
        """Creates the stage_events table if it doesn't exist. Safe to
        call on every startup — no migration framework needed for a
        single append-only table like this."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def log_stage_event(
        self,
        track_id: str,
        stage: str,
        severity: str,
        confidence: float,
        contributing_sources: list[str],
        timestamp: datetime,
    ) -> None:
        async with self._session_factory() as session:
            session.add(
                StageEvent(
                    track_id=track_id,
                    stage=stage,
                    severity=severity,
                    confidence=confidence,
                    contributing_sources=",".join(contributing_sources),
                    timestamp=timestamp,
                )
            )
            await session.commit()

    async def get_track_history(self, track_id: str) -> list[dict]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(StageEvent).where(StageEvent.track_id == track_id).order_by(StageEvent.timestamp)
            )
            return [self._to_dict(row) for row in result.scalars().all()]

    async def get_recent_history(self, limit: int = 100) -> list[dict]:
        async with self._session_factory() as session:
            result = await session.execute(select(StageEvent).order_by(StageEvent.timestamp.desc()).limit(limit))
            return [self._to_dict(row) for row in result.scalars().all()]

    @staticmethod
    def _to_dict(row: StageEvent) -> dict:
        return {
            "track_id": row.track_id,
            "stage": row.stage,
            "severity": row.severity,
            "confidence": row.confidence,
            "contributing_sources": row.contributing_sources.split(",") if row.contributing_sources else [],
            "timestamp": row.timestamp.isoformat(),
        }

    async def dispose(self) -> None:
        """Closes the engine's connection pool — used on app shutdown and
        in tests to avoid leaking connections across test runs."""
        await self._engine.dispose()


# App-wide singleton, matching fusion_engine/ew_simulator's pattern.
# Defaults to a local SQLite file; set DATABASE_URL to a postgres:// URL
# to use Postgres instead — same code path either way.
history_store = HistoryStore(settings.DATABASE_URL or "sqlite:///./sentinel.db")
