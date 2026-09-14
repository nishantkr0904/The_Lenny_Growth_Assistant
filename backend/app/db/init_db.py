"""Database schema initialization."""

from pathlib import Path
from sqlalchemy import text
from app.core.logging import get_logger
from app.db.session import engine

logger = get_logger(__name__)

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def init_db() -> None:
    """Initialize database schema idempotently from schema.sql."""
    if not SCHEMA_PATH.exists():
        logger.error("schema.sql not found at %s", SCHEMA_PATH)
        raise FileNotFoundError(f"schema.sql not found at {SCHEMA_PATH}")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    logger.info("Applying database schema from schema.sql...")
    async with engine.begin() as conn:
        # Split statements by semicolon to execute sequentially
        statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]
        for stmt in statements:
            await conn.execute(text(stmt))

    logger.info("Database schema initialized successfully.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(init_db())
