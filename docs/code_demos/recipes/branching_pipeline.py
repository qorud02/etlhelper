"""Run a branching bird quality-check pipeline using two in-memory SQLite databases."""
from collections.abc import Iterable, Iterator
from contextlib import closing
import re
import sqlite3
from typing import Any

import etlhelper as etl


def check_birds(rows: Iterable[dict[str, Any]]) -> Iterator[tuple[dict[str, Any], dict[str, Any] | None]]:
    """Return a size check and, for swimming birds, a second output row."""
    for row in rows:
        size_check = {
            "id": row["id"],
            "name": row["name"],
            "fly_through_window": row["wingspan"] < 60,
        }
        swimming_bird = None
        if re.search(r"(Goose|Duck|Penguin|Gull)", row["name"], re.IGNORECASE):
            swimming_bird = {"id": row["id"], "name": row["name"], "can_swim": True}
        yield size_check, swimming_bird


def qa_birds(source_conn: sqlite3.Connection, dest_conn: sqlite3.Connection, chunk_size: int = 2) -> None:
    """Extract once and load each transformed chunk into two destination tables."""
    chunks = etl.iter_chunks(
        "SELECT id, name, wingspan FROM birds ORDER BY id",
        source_conn,
        transform=check_birds,
        chunk_size=chunk_size,
    )
    for chunk in chunks:
        size_rows = []
        swim_rows = []
        for size_check, swimming_bird in chunk:
            size_rows.append(size_check)
            if swimming_bird is not None:
                swim_rows.append(swimming_bird)
        etl.load("birds_size_qa", dest_conn, size_rows)
        etl.load("birds_swim_qa", dest_conn, swim_rows)


def create_tables(source_conn: sqlite3.Connection, dest_conn: sqlite3.Connection) -> None:
    """Create the source table and both destination tables."""
    etl.execute("""
        CREATE TABLE birds (id INTEGER PRIMARY KEY, name TEXT, wingspan FLOAT)
        """, source_conn)
    etl.execute("""
        CREATE TABLE birds_size_qa
            (id INTEGER PRIMARY KEY, name TEXT, fly_through_window BOOLEAN)
        """, dest_conn)
    etl.execute("""
        CREATE TABLE birds_swim_qa
            (id INTEGER PRIMARY KEY, name TEXT, can_swim BOOLEAN)
        """, dest_conn)


def main() -> None:
    """Populate sample data and print the results without creating database files."""
    birds = [
        {"id": 1, "name": "Barn Swallow", "wingspan": 30},
        {"id": 2, "name": "European Robin", "wingspan": 22},
        {"id": 3, "name": "Mallard Duck", "wingspan": 81},
        {"id": 4, "name": "Canada Goose", "wingspan": 170},
    ]
    with closing(sqlite3.connect(":memory:")) as source_conn, closing(sqlite3.connect(":memory:")) as dest_conn:
        create_tables(source_conn, dest_conn)
        etl.load("birds", source_conn, birds)
        qa_birds(source_conn, dest_conn)
        print("Size checks:", etl.fetchall("SELECT * FROM birds_size_qa ORDER BY id", dest_conn))
        print("Swimming birds:", etl.fetchall("SELECT * FROM birds_swim_qa ORDER BY id", dest_conn))


if __name__ == "__main__":
    main()
