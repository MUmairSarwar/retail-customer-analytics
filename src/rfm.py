import pandas as pd


def _quintile_score(series: pd.Series, high_is_good: bool = True) -> pd.Series:
    """Create stable quintile scores even when values contain many ties."""
    ranked = series.rank(method="first")
    score = pd.qcut(ranked, 5, labels=[1, 2, 3, 4, 5]).astype(int)
    return score if high_is_good else 6 - score


def assign_segment(row: pd.Series) -> str:
    r, f, m = row["r_score"], row["f_score"], row["m_score"]
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if r >= 3 and f >= 4:
        return "Loyal"
    if r >= 4 and f in (2, 3):
        return "Potential loyalists"
    if r <= 2 and f >= 3:
        return "At risk"
    if r <= 2 and f <= 2:
        return "Hibernating"
    return "Needs attention"


def build_rfm(sales: pd.DataFrame) -> pd.DataFrame:
    """Build recency-frequency-monetary customer segments from valid sales."""
    known = sales.dropna(subset=["customer_id"]).copy()
    if known.empty:
        raise ValueError("Customer IDs are required for RFM analysis")

    reference_date = known["invoice_date"].max().normalize() + pd.Timedelta(days=1)
    rfm = (
        known.groupby("customer_id")
        .agg(
            last_purchase=("invoice_date", "max"),
            frequency=("invoice_no", "nunique"),
            monetary=("line_value", "sum"),
        )
        .reset_index()
    )
    rfm["recency_days"] = (reference_date - rfm["last_purchase"].dt.normalize()).dt.days
    rfm["r_score"] = _quintile_score(rfm["recency_days"], high_is_good=False)
    rfm["f_score"] = _quintile_score(rfm["frequency"], high_is_good=True)
    rfm["m_score"] = _quintile_score(rfm["monetary"], high_is_good=True)
    rfm["rfm_score"] = rfm[["r_score", "f_score", "m_score"]].sum(axis=1)
    rfm["segment"] = rfm.apply(assign_segment, axis=1)
    return rfm.sort_values(["rfm_score", "monetary"], ascending=False)

