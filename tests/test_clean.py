import pandas as pd

from src.clean import clean_transactions


def sample_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "InvoiceNo": ["100", "C101", "102", "103"],
            "StockCode": ["A", "A", "B", "C"],
            "Description": ["Item A", "Item A", None, "Free sample"],
            "Quantity": [2, -1, 3, 1],
            "InvoiceDate": ["2011-01-01"] * 4,
            "UnitPrice": [5.0, 5.0, 2.0, 0.0],
            "CustomerID": [1, 1, None, 2],
            "Country": ["United Kingdom"] * 4,
        }
    )


def test_cleaning_flags_only_valid_sale() -> None:
    result = clean_transactions(sample_data())
    assert result["is_valid_sale"].tolist() == [True, False, False, False]
    assert result["is_cancellation"].tolist() == [False, True, False, False]


def test_line_value_and_nullable_customer_id() -> None:
    result = clean_transactions(sample_data())
    assert result.loc[0, "line_value"] == 10.0
    assert pd.isna(result.loc[2, "customer_id"])

