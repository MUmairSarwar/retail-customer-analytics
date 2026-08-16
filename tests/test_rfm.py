import pandas as pd

from src.rfm import build_rfm


def test_rfm_creates_one_row_per_customer() -> None:
    rows = []
    for customer in range(1, 11):
        for order in range(1, customer + 1):
            rows.append(
                {
                    "customer_id": customer,
                    "invoice_date": pd.Timestamp("2011-12-01") - pd.Timedelta(days=customer * 3 + order),
                    "invoice_no": f"{customer}-{order}",
                    "line_value": float(customer * 10),
                }
            )
    result = build_rfm(pd.DataFrame(rows))
    assert len(result) == 10
    assert result["customer_id"].nunique() == 10
    assert result["segment"].notna().all()
    assert result["rfm_score"].between(3, 15).all()

