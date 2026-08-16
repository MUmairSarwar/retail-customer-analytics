import json
import sqlite3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.clean import clean_transactions
from src.download_data import download_dataset
from src.paths import DATABASE, FIGURES_DIR, PROCESSED_DIR, RAW_XLSX, REPORTS_DIR, ensure_directories
from src.rfm import build_rfm


COLORS = {
    "navy": "#17324D",
    "blue": "#2F75B5",
    "teal": "#3A8D8D",
    "orange": "#D9822B",
    "grey": "#7A8793",
    "light": "#E8EEF3",
}


def money(value: float) -> str:
    return f"£{value:,.0f}"


def build_summary_tables(data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    sales = data[data["is_valid_sale"]].copy()
    returns = data[data["is_cancellation"] & data["line_value"].lt(0)].copy()

    monthly_sales = (
        sales.groupby("year_month")
        .agg(revenue=("line_value", "sum"), orders=("invoice_no", "nunique"), units=("quantity", "sum"), customers=("customer_id", "nunique"))
        .reset_index()
    )
    monthly_returns = (
        returns.assign(return_value=lambda x: x["line_value"].abs(), return_units=lambda x: x["quantity"].abs())
        .groupby("year_month")
        .agg(return_value=("return_value", "sum"), return_units=("return_units", "sum"), cancelled_orders=("invoice_no", "nunique"))
        .reset_index()
    )
    monthly = monthly_sales.merge(monthly_returns, on="year_month", how="left").fillna(0)
    monthly["average_order_value"] = monthly["revenue"] / monthly["orders"]
    monthly["return_value_rate"] = monthly["return_value"] / (monthly["revenue"] + monthly["return_value"])

    country_sales = (
        sales.groupby("country")
        .agg(revenue=("line_value", "sum"), orders=("invoice_no", "nunique"), units=("quantity", "sum"), customers=("customer_id", "nunique"))
        .reset_index()
    )
    country_returns = (
        returns.assign(return_value=lambda x: x["line_value"].abs())
        .groupby("country")
        .agg(return_value=("return_value", "sum"), cancelled_orders=("invoice_no", "nunique"))
        .reset_index()
    )
    countries = country_sales.merge(country_returns, on="country", how="left").fillna(0)
    countries["average_order_value"] = countries["revenue"] / countries["orders"]
    countries["return_value_rate"] = countries["return_value"] / (countries["revenue"] + countries["return_value"])
    countries = countries.sort_values("revenue", ascending=False)

    product_sales = (
        sales.groupby(["stock_code", "description"])
        .agg(revenue=("line_value", "sum"), sold_units=("quantity", "sum"), orders=("invoice_no", "nunique"))
        .reset_index()
    )
    product_returns = (
        returns.assign(return_value=lambda x: x["line_value"].abs(), return_units=lambda x: x["quantity"].abs())
        .groupby("stock_code")
        .agg(return_value=("return_value", "sum"), return_units=("return_units", "sum"), cancelled_orders=("invoice_no", "nunique"))
        .reset_index()
    )
    products = product_sales.merge(product_returns, on="stock_code", how="left").fillna(0)
    products["return_unit_rate"] = products["return_units"] / (products["sold_units"] + products["return_units"])
    products = products.sort_values("revenue", ascending=False)

    customers = build_rfm(sales)
    segments = (
        customers.groupby("segment")
        .agg(customers=("customer_id", "nunique"), revenue=("monetary", "sum"), median_recency_days=("recency_days", "median"), median_orders=("frequency", "median"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    segments["customer_share"] = segments["customers"] / segments["customers"].sum()
    segments["revenue_share"] = segments["revenue"] / segments["revenue"].sum()

    return {
        "monthly_kpis": monthly,
        "country_kpis": countries,
        "product_kpis": products,
        "customer_rfm": customers,
        "segment_kpis": segments,
    }


def calculate_kpis(data: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> dict[str, float | int | str]:
    sales = data[data["is_valid_sale"]]
    returns = data[data["is_cancellation"] & data["line_value"].lt(0)]
    customers = tables["customer_rfm"]
    revenue = float(sales["line_value"].sum())
    return_value = float(returns["line_value"].abs().sum())
    customer_revenue = customers["monetary"].sort_values(ascending=False)
    top_n = max(1, int(np.ceil(len(customer_revenue) * 0.10)))
    known_customer_revenue = float(customer_revenue.sum())

    return {
        "source_rows": int(len(data)),
        "valid_sales_rows": int(sales.shape[0]),
        "excluded_rows": int((~data["is_valid_sale"]).sum()),
        "missing_customer_id_rows": int(data["customer_id"].isna().sum()),
        "missing_customer_id_rate": float(data["customer_id"].isna().mean()),
        "revenue": revenue,
        "return_value": return_value,
        "return_value_rate": return_value / (revenue + return_value),
        "orders": int(sales["invoice_no"].nunique()),
        "customers": int(sales["customer_id"].nunique()),
        "average_order_value": revenue / sales["invoice_no"].nunique(),
        "repeat_customer_rate": float((customers["frequency"] >= 2).mean()),
        "top_10pct_customer_revenue_share": float(customer_revenue.head(top_n).sum() / known_customer_revenue),
        "date_start": str(data["invoice_date"].min().date()),
        "date_end": str(data["invoice_date"].max().date()),
    }


def save_tables(tables: dict[str, pd.DataFrame]) -> None:
    for name, table in tables.items():
        table.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)


def build_database(data: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> None:
    export = data.copy()
    export["invoice_date"] = export["invoice_date"].astype(str)
    export["customer_id"] = export["customer_id"].astype("string")
    export["year"] = export["year"].astype("string")
    export["month"] = export["month"].astype("string")
    export["hour"] = export["hour"].astype("string")
    temporary_database = DATABASE.with_suffix(".tmp")
    temporary_database.unlink(missing_ok=True)
    connection = sqlite3.connect(temporary_database)
    try:
        export.to_sql("transactions", connection, if_exists="replace", index=False, chunksize=20_000)
        for name, table in tables.items():
            table.to_sql(name, connection, if_exists="replace", index=False)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_invoice ON transactions(invoice_no)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_customer ON transactions(customer_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_product ON transactions(stock_code)")
        connection.commit()
    finally:
        connection.close()
    temporary_database.replace(DATABASE)


def save_figures(tables: dict[str, pd.DataFrame]) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    monthly = tables["monthly_kpis"]
    countries = (
        tables["country_kpis"]
        .loc[lambda x: x["country"] != "United Kingdom"]
        .head(8)
        .sort_values("revenue")
    )
    segments = tables["segment_kpis"].sort_values("revenue")
    risky = tables["product_kpis"].query("sold_units >= 100 and return_units >= 10").nlargest(8, "return_unit_rate").sort_values("return_unit_rate")

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    axes[0, 0].plot(monthly["year_month"], monthly["revenue"] / 1_000, marker="o", color=COLORS["blue"], linewidth=2)
    axes[0, 0].set_title("Monthly sales revenue")
    axes[0, 0].set_ylabel("£ thousands")
    axes[0, 0].tick_params(axis="x", rotation=45)

    axes[0, 1].barh(countries["country"], countries["revenue"] / 1_000, color=COLORS["teal"])
    axes[0, 1].set_title("Top non-UK countries by revenue")
    axes[0, 1].set_xlabel("£ thousands")

    axes[1, 0].barh(segments["segment"], segments["revenue"] / 1_000, color=COLORS["blue"])
    axes[1, 0].set_title("Revenue by customer segment")
    axes[1, 0].set_xlabel("£ thousands")

    axes[1, 1].barh(risky["description"].str.title().str.slice(0, 31), risky["return_unit_rate"] * 100, color=COLORS["orange"])
    axes[1, 1].set_title("Products with high return rates*")
    axes[1, 1].set_xlabel("Returned units / total units (%)")
    axes[1, 1].text(0, -0.18, "*At least 100 sold and 10 returned units", transform=axes[1, 1].transAxes, fontsize=9, color=COLORS["grey"])

    fig.suptitle("Retail Customer & Operations Dashboard", fontsize=18, fontweight="bold", color=COLORS["navy"])
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    fig.savefig(FIGURES_DIR / "dashboard_overview.png", dpi=180, bbox_inches="tight")
    fig.savefig(FIGURES_DIR / "dashboard_overview.svg", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(monthly["year_month"], monthly["revenue"], marker="o", linewidth=2.5, color=COLORS["blue"])
    ax.fill_between(monthly["year_month"], monthly["revenue"], alpha=0.12, color=COLORS["blue"])
    ax.set_title("Monthly sales revenue", fontsize=15, fontweight="bold")
    ax.set_ylabel("Revenue (£)")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "monthly_revenue.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_report(kpis: dict, tables: dict[str, pd.DataFrame]) -> None:
    monthly = tables["monthly_kpis"]
    countries = tables["country_kpis"]
    segments = tables["segment_kpis"]
    risky = tables["product_kpis"].query("sold_units >= 100 and return_units >= 10").nlargest(5, "return_unit_rate")
    best_month = monthly.loc[monthly["revenue"].idxmax()]
    top_non_uk = countries[countries["country"] != "United Kingdom"].iloc[0]
    at_risk = segments.loc[segments["segment"].eq("At risk")].iloc[0]

    lines = [
        "# Executive summary",
        "",
        "## Business problem",
        "",
        "A retail manager needs a reliable view of sales, cancelled orders and customer behaviour so that marketing and operations teams can focus on the right customers, markets and products.",
        "",
        "## Main findings",
        "",
        f"- Valid sales generated **{money(kpis['revenue'])}** from **{kpis['orders']:,} orders**. Average order value was **{money(kpis['average_order_value'])}**.",
        f"- Cancelled and returned lines represented **{money(kpis['return_value'])}**, or **{kpis['return_value_rate']:.1%}** of sales plus return value.",
        f"- The strongest month was **{best_month['year_month']}**, with **{money(best_month['revenue'])}** in sales.",
        f"- Outside the UK, **{top_non_uk['country']}** was the largest market with **{money(top_non_uk['revenue'])}** in sales.",
        f"- **{kpis['repeat_customer_rate']:.1%}** of identified customers placed at least two orders.",
        f"- The top 10% of identified customers generated **{kpis['top_10pct_customer_revenue_share']:.1%}** of known-customer revenue.",
        f"- The **At risk** segment contains **{int(at_risk['customers']):,} customers** and represents **{money(at_risk['revenue'])}** in historical sales.",
        "",
        "## Recommended actions",
        "",
        "1. Contact high-value At risk customers with a targeted reactivation offer instead of sending one campaign to everyone.",
        "2. Review the highest-cancellation products for data-entry, description, packing or fulfilment problems before increasing promotion.",
        "3. Plan staffing and stock earlier for the seasonal sales peak visible in the monthly trend.",
        f"4. Protect data quality: **{kpis['missing_customer_id_rate']:.1%}** of source rows have no customer ID, so customer-level results should not be treated as a complete view of all sales.",
        "5. Test selected non-UK markets, starting with the strongest current market, while tracking order value and return rate.",
        "",
        "## Products to review",
        "",
    ]
    for row in risky.itertuples():
        lines.append(f"- {str(row.description).title()}: {row.return_unit_rate:.1%} unit return rate ({int(row.return_units):,} returned units).")
    lines += [
        "",
        "## Important limitations",
        "",
        "- The data covers one retailer and about one year, so results should not be generalised to all retail businesses.",
        "- Customer IDs are missing for some transactions. These sales are included in sales KPIs but excluded from RFM segmentation.",
        "- A cancelled line is treated as a return/cancellation signal. The dataset does not provide a reason code, margin or inventory cost.",
        "- The final December 2011 period is incomplete and should not be compared directly with full months.",
    ]
    (REPORTS_DIR / "executive_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_pipeline() -> None:
    ensure_directories()
    download_dataset()
    print("Reading and cleaning transactions...")
    raw = pd.read_excel(RAW_XLSX)
    data = clean_transactions(raw)
    print("Building analysis tables...")
    tables = build_summary_tables(data)
    kpis = calculate_kpis(data, tables)
    save_tables(tables)
    (PROCESSED_DIR / "kpis.json").write_text(json.dumps(kpis, indent=2), encoding="utf-8")
    print("Building SQLite database and charts...")
    build_database(data, tables)
    save_figures(tables)
    save_report(kpis, tables)
    print("Analysis complete.")


if __name__ == "__main__":
    run_pipeline()
