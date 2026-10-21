import re

import backend.app.infrastructure.models  # noqa: F401  (registers every table)
from backend.app.infrastructure.database import Base

SNAKE_CASE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")


def test_ar13_tables_and_columns_are_snake_case_and_every_table_has_timestamps() -> None:
    tables = Base.metadata.sorted_tables
    assert tables, "no tables found; the models are not registered"
    names = [table.name for table in tables] + [
        f"{table.name}.{column.name}" for table in tables for column in table.columns
    ]
    assert [name for name in names if not all(SNAKE_CASE.match(part) for part in name.split("."))] == []
    assert [table.name for table in tables if not {"created_at", "updated_at"} <= set(table.columns.keys())] == []
