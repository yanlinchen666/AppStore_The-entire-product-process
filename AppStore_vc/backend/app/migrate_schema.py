"""
Database migration script.
Adds new columns to existing tables to support:
- AnalysisFinding.is_assumption, validation_status, finding_type, impact
- PRDRequirement.description, user_value, business_value, estimated_effort

Usage:
    python -m app.migrate_schema
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from sqlalchemy import text
from app.database import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def column_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(
        text("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table
              AND COLUMN_NAME = :column
        """),
        {"table": table, "column": column},
    )
    return result.scalar() > 0


def add_column_if_missing(conn, table: str, column: str, ddl_type: str):
    if column_exists(conn, table, column):
        logger.info(f"  [skip] {table}.{column} already exists")
        return
    sql = f"ALTER TABLE `{table}` ADD COLUMN `{column}` {ddl_type}"
    logger.info(f"  [add]  {sql}")
    conn.execute(text(sql))


def migrate():
    logger.info("Starting schema migration...")

    migrations = [
        # AnalysisFinding new columns
        ("analysis_findings", "finding_type", "VARCHAR(50) NULL"),
        ("analysis_findings", "impact", "VARCHAR(20) NULL"),
        ("analysis_findings", "is_assumption", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("analysis_findings", "validation_status", "VARCHAR(30) NOT NULL DEFAULT 'validated'"),
        # PRDRequirement new columns
        ("prd_requirements", "description", "TEXT NULL"),
        ("prd_requirements", "user_value", "TEXT NULL"),
        ("prd_requirements", "business_value", "TEXT NULL"),
        ("prd_requirements", "estimated_effort", "VARCHAR(50) NULL"),
    ]

    with engine.begin() as conn:
        for table, column, ddl_type in migrations:
            try:
                add_column_if_missing(conn, table, column, ddl_type)
            except Exception as e:
                logger.error(f"  [error] Failed to migrate {table}.{column}: {e}")

    logger.info("Migration completed.")


if __name__ == "__main__":
    migrate()
