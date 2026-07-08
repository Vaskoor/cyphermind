"""SQLAlchemy async engine and session factory."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Create all tables and apply lightweight schema migrations."""
    from app.models import user, engagement, learning, knowledge, selfplay, attack_memory  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_report_columns)


def _migrate_report_columns(connection):
    """Add new Report columns on existing SQLite DBs."""
    import sqlalchemy as sa
    from sqlalchemy import inspect, text

    inspector = inspect(connection)
    if "reports" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("reports")}
    alters = [
        ("agent_run_id", "INTEGER"),
        ("report_type", "VARCHAR(32) DEFAULT 'combined'"),
        ("agent_name", "VARCHAR(64)"),
        ("findings_count", "INTEGER DEFAULT 0"),
    ]
    for col, typedef in alters:
        if col not in existing:
            try:
                connection.execute(text(f"ALTER TABLE reports ADD COLUMN {col} {typedef}"))
            except Exception:
                pass
