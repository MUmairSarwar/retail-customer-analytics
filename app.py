import json
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"

st.set_page_config(page_title="Retail Customer Analytics", page_icon="📊", layout="wide")


@st.cache_data
def load_data():
    with (DATA / "kpis.json").open(encoding="utf-8") as file:
        kpis = json.load(file)
    monthly = pd.read_csv(DATA / "monthly_kpis.csv")
    countries = pd.read_csv(DATA / "country_kpis.csv")
    products = pd.read_csv(DATA / "product_kpis.csv")
    customers = pd.read_csv(DATA / "customer_rfm.csv")
    segments = pd.read_csv(DATA / "segment_kpis.csv")
    return kpis, monthly, countries, products, customers, segments


def pounds(value: float) -> str:
    return f"£{value:,.0f}"


kpis, monthly, countries, products, customers, segments = load_data()

st.title("Retail Customer & Operations Analytics")
st.caption(f"UCI Online Retail data | {kpis['date_start']} to {kpis['date_end']}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Sales revenue", pounds(kpis["revenue"]))
c2.metric("Orders", f"{kpis['orders']:,}")
c3.metric("Average order value", pounds(kpis["average_order_value"]))
c4.metric("Return value rate", f"{kpis['return_value_rate']:.1%}")

tab1, tab2, tab3 = st.tabs(["Performance", "Customers", "Product returns"])

with tab1:
    st.subheader("Monthly performance")
    st.line_chart(monthly.set_index("year_month")[["revenue"]], color="#2F75B5")
    left, right = st.columns(2)
    with left:
        st.subheader("Largest markets")
        st.bar_chart(countries.head(10).set_index("country")[["revenue"]], horizontal=True, color="#3A8D8D")
    with right:
        st.subheader("Data-quality note")
        st.write(
            f"{kpis['missing_customer_id_rate']:.1%} of source rows have no customer ID. "
            "They remain in sales KPIs but are excluded from customer segmentation."
        )
        st.write("December 2011 is incomplete, so it is not directly comparable with full months.")

with tab2:
    st.subheader("Customer segments")
    st.bar_chart(segments.set_index("segment")[["revenue"]], horizontal=True, color="#2F75B5")
    selected_segment = st.selectbox("Inspect a segment", segments["segment"].tolist())
    view = customers.loc[customers["segment"].eq(selected_segment), ["customer_id", "recency_days", "frequency", "monetary", "segment"]]
    st.dataframe(view.sort_values("monetary", ascending=False).head(25), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Products to investigate")
    st.write("The filter avoids ranking products from only a few transactions.")
    min_sold = st.slider("Minimum units sold", 25, 500, 100, 25)
    min_returned = st.slider("Minimum returned units", 1, 100, 10)
    risky = products.loc[(products["sold_units"] >= min_sold) & (products["return_units"] >= min_returned)].nlargest(20, "return_unit_rate")
    st.dataframe(
        risky[["stock_code", "description", "sold_units", "return_units", "return_unit_rate", "revenue"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "return_unit_rate": st.column_config.NumberColumn("Return rate", format="%.1%%"),
            "revenue": st.column_config.NumberColumn("Revenue", format="£%.2f"),
        },
    )

st.divider()
st.caption("Built by Muhammad Umair Sarwar. Definitions, SQL queries and limitations are documented in the repository.")

