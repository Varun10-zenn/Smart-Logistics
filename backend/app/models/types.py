"""Dialect-aware column types shared by all SQLAlchemy models."""
from sqlalchemy import DateTime
from sqlalchemy.dialects.mysql import DATETIME as MySQLDATETIME

# PostgreSQL: TIMESTAMP WITH TIME ZONE (unchanged behaviour).
# MySQL 8: no time-zone aware timestamp type, so use DATETIME(6) to keep the
# microsecond precision that DateTime(timezone=True) provides on PostgreSQL.
TZDateTime = DateTime(timezone=True).with_variant(
    MySQLDATETIME(fsp=6, timezone=True), "mysql"
)
