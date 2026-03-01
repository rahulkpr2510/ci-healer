# backend/app/db/database.py

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
import logging

from config.settings import settings

logger = logging.getLogger(__name__)

# ── Naming convention for Alembic migrations ──────────────
# This ensures FK/index names are deterministic across DBs
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# ── Declarative base all models inherit from ──────────────
class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# ── Async engine ──────────────────────────────────────────
_is_sqlite = settings.async_database_url.startswith("sqlite")
_is_postgres = settings.async_database_url.startswith("postgresql")

# Build engine kwargs based on database type
_engine_kwargs = {}
if not _is_sqlite:
    _engine_kwargs = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 300,  # Recycle connections every 5 min for PgBouncer compatibility
    }
    # Add SSL for PostgreSQL (required for Supabase/Neon)
    if _is_postgres:
        # statement_cache_size=0 required for Supabase/PgBouncer transaction pooler
        _engine_kwargs["connect_args"] = {
            "ssl": "require",
            "statement_cache_size": 0,
        }

engine = create_async_engine(
    settings.async_database_url,
    echo=settings.DEBUG,
    **_engine_kwargs,
)

# ── Session factory ───────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,        # prevent lazy-load errors after commit
    autoflush=False,
    autocommit=False,
)


# ── FastAPI dependency ────────────────────────────────────
# Use this in every router: db: AsyncSession = Depends(get_db)
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Startup / shutdown helpers ────────────────────────────
# Called in app/main.py lifespan
async def init_db() -> None:
    """
    Creates all tables on startup (dev only).
    In production, Alembic migrations handle this.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables initialised")


async def close_db() -> None:
    await engine.dispose()
    logger.info("✅ Database connection pool closed")
