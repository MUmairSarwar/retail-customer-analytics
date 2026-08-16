import sqlite3
from pathlib import Path


def test_generated_database_contains_expected_tables_and_rows() -> None:
    database = Path(__file__).resolve().parents[1] / "data" / "processed" / "retail.db"
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert {
            "transactions",
            "monthly_kpis",
            "country_kpis",
            "product_kpis",
            "customer_rfm",
            "segment_kpis",
        }.issubset(tables)
        assert connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 541_909

