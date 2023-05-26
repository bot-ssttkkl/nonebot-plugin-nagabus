from ...config import conf

dialect = conf.datastore_database_dialect
if dialect == 'sqlite':
    from sqlalchemy.dialects.sqlite import insert as _insert
    from sqlalchemy.dialects.sqlite import JSON as _JSON
    from sqlalchemy.dialects.sqlite import BLOB as _BLOB
elif dialect == 'postgresql':
    from sqlalchemy.dialects.postgresql import insert as _insert
    from sqlalchemy.dialects.postgresql import JSONB as _JSON
    from sqlalchemy.dialects.postgresql import BYTEA as _BLOB
else:
    raise RuntimeError(f"Unsupported SQL dialect: {dialect}")

insert = _insert
JSON = _JSON
BLOB = _BLOB

from .utc_datetime import UTCDateTime

__all__ = ("insert", "JSON", "BLOB", "UTCDateTime")
