import pandas as pd


REQUIRED_COLUMNS = {
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
}

RENAME_COLUMNS = {
    "InvoiceNo": "invoice_no",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_date",
    "UnitPrice": "unit_price",
    "CustomerID": "customer_id",
    "Country": "country",
}


def clean_transactions(raw: pd.DataFrame) -> pd.DataFrame:
    """Standardise fields and add transparent quality and transaction flags."""
    missing = REQUIRED_COLUMNS.difference(raw.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = raw.rename(columns=RENAME_COLUMNS).copy()
    data["invoice_no"] = data["invoice_no"].astype("string").str.strip()
    data["stock_code"] = data["stock_code"].astype("string").str.strip()
    data["description"] = data["description"].astype("string").str.strip()
    data["country"] = data["country"].astype("string").str.strip()
    data["invoice_date"] = pd.to_datetime(data["invoice_date"], errors="coerce")
    data["quantity"] = pd.to_numeric(data["quantity"], errors="coerce")
    data["unit_price"] = pd.to_numeric(data["unit_price"], errors="coerce")
    data["customer_id"] = pd.to_numeric(data["customer_id"], errors="coerce").astype("Int64")

    data["line_value"] = data["quantity"] * data["unit_price"]
    data["is_cancellation"] = data["invoice_no"].str.startswith("C", na=False) | data[
        "quantity"
    ].lt(0)
    data["is_valid_sale"] = (
        ~data["is_cancellation"]
        & data["quantity"].gt(0)
        & data["unit_price"].gt(0)
        & data["description"].notna()
        & data["invoice_date"].notna()
    )
    data["year_month"] = data["invoice_date"].dt.to_period("M").astype("string")
    data["year"] = data["invoice_date"].dt.year.astype("Int64")
    data["month"] = data["invoice_date"].dt.month.astype("Int64")
    data["weekday"] = data["invoice_date"].dt.day_name()
    data["hour"] = data["invoice_date"].dt.hour.astype("Int64")
    return data

