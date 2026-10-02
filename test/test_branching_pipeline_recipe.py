"""Offline tests for the runnable branching-pipeline recipe."""
from contextlib import closing
from pathlib import Path
import runpy
import sqlite3

import pytest

import etlhelper as etl


RECIPE_PATH = Path(__file__).resolve().parents[1] / "docs/code_demos/recipes/branching_pipeline.py"


@pytest.fixture
def recipe():
    return runpy.run_path(str(RECIPE_PATH))


@pytest.mark.parametrize("chunk_size", [1, 2, 5])
def test_branches_load_different_rows_across_chunks(recipe, chunk_size):
    birds = [
        {"id": 1, "name": "Barn Swallow", "wingspan": 30},
        {"id": 2, "name": "European Robin", "wingspan": 22},
        {"id": 3, "name": "Mallard Duck", "wingspan": 81},
        {"id": 4, "name": "Canada Goose", "wingspan": 170},
    ]
    with closing(sqlite3.connect(":memory:")) as source_conn, closing(sqlite3.connect(":memory:")) as dest_conn:
        recipe["create_tables"](source_conn, dest_conn)
        etl.load("birds", source_conn, birds)
        recipe["qa_birds"](source_conn, dest_conn, chunk_size=chunk_size)

        size_rows = etl.fetchall("SELECT * FROM birds_size_qa ORDER BY id", dest_conn)
        assert size_rows == [
            {"id": 1, "name": "Barn Swallow", "fly_through_window": 1},
            {"id": 2, "name": "European Robin", "fly_through_window": 1},
            {"id": 3, "name": "Mallard Duck", "fly_through_window": 0},
            {"id": 4, "name": "Canada Goose", "fly_through_window": 0},
        ]
        assert etl.fetchall("SELECT * FROM birds_swim_qa ORDER BY id", dest_conn) == [
            {"id": 3, "name": "Mallard Duck", "can_swim": 1},
            {"id": 4, "name": "Canada Goose", "can_swim": 1},
        ]


def test_branch_can_remain_empty(recipe):
    with closing(sqlite3.connect(":memory:")) as source_conn, closing(sqlite3.connect(":memory:")) as dest_conn:
        recipe["create_tables"](source_conn, dest_conn)
        etl.load("birds", source_conn, [
            {"id": 1, "name": "Barn Swallow", "wingspan": 30},
            {"id": 2, "name": "European Robin", "wingspan": 22},
        ])
        recipe["qa_birds"](source_conn, dest_conn, chunk_size=1)
        assert len(etl.fetchall("SELECT * FROM birds_size_qa", dest_conn)) == 2
        assert etl.fetchall("SELECT * FROM birds_swim_qa", dest_conn) == []


def test_empty_source_leaves_both_branches_empty(recipe):
    with closing(sqlite3.connect(":memory:")) as source_conn, closing(sqlite3.connect(":memory:")) as dest_conn:
        recipe["create_tables"](source_conn, dest_conn)
        recipe["qa_birds"](source_conn, dest_conn)
        assert etl.fetchall("SELECT * FROM birds_size_qa", dest_conn) == []
        assert etl.fetchall("SELECT * FROM birds_swim_qa", dest_conn) == []


def test_recipe_runs_as_script(capsys):
    runpy.run_path(str(RECIPE_PATH), run_name="__main__")
    output = capsys.readouterr().out.splitlines()
    assert output[0].startswith("Size checks: ")
    assert "Barn Swallow" in output[0]
    assert "Canada Goose" in output[0]
    assert output[1] == (
        "Swimming birds: [{'id': 3, 'name': 'Mallard Duck', 'can_swim': 1}, "
        "{'id': 4, 'name': 'Canada Goose', 'can_swim': 1}]"
    )
