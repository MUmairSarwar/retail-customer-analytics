import sqlite3

import pandas as pd

from src.clean import clean_transactions
from src.pipeline import build_database


def test_generated_database_contains_expected_tables_and_rows(tmp_path) -> None:
    raw = pd.DataFrame(
        {
            "InvoiceNo": ["100", "C101"],
            "StockCode": ["A", "A"],
            "Description": ["Item A", "Item A"],
            "Quantity": [2, -1],
            "InvoiceDate": ["2011-01-01", "2011-01-02"],
            "UnitPrice": [5.0, 5.0],
            "CustomerID": [1, 1],
            "Country": ["United Kingdom", "United Kingdom"],
        }
    )
    data = clean_transactions(raw)
    expected_tables = {
        "monthly_kpis",
        "country_kpis",
        "product_kpis",
        "customer_rfm",
        "segment_kpis",
    }
    tables = {name: pd.DataFrame({"value": [1]}) for name in expected_tables}
    database = tmp_path / "retail.db"
    build_database(data, tables, database_path=database)

    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert expected_tables.union({"transactions"}).issubset(tables)
        assert connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 2
