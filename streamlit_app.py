import streamlit as st
import altair as alt

from utils.loader import load_all_data
from utils.cleaner import (
    clean_data,
    melt_ownership,
    map_investor_category
)

# ===============================
# PAGE SETUP
# ===============================
st.set_page_config(
    page_title="Dashboard Kepemilikan Saham",
    layout="wide"
)

st.title("📊 Kepemilikan Saham per Bulan (Equity Only)")

# ===============================
# LOAD & PREPARE DATA
# ===============================
raw_df = load_all_data()
clean_df = clean_data(raw_df)
long_df = melt_ownership(clean_df)
long_df = map_investor_category(long_df)


# ===============================
# SIDEBAR FILTER
# ===============================
st.sidebar.header("Filter")

selected_code = st.sidebar.selectbox(
    "Pilih Saham",
    sorted(long_df["Code"].unique())
)

filtered_df = long_df[
    long_df["Code"] == selected_code
].copy()

# ===============================
# CATEGORY FILTER
# ===============================
available_categories = sorted(
    filtered_df["Category_Label"].dropna().unique()
)

if len(available_categories) == 0:
    st.warning("Tidak ada data equity untuk saham ini.")
    st.stop()

categories = st.sidebar.multiselect(
    "Pilih Kategori Investor",
    options=available_categories,
    default=available_categories[:4]
)

filtered_df = filtered_df[
    filtered_df["Category_Label"].isin(categories)
]

filtered_df = long_df[long_df["Code"] == selected_code].copy()

# =========================================
# PILIH BULAN YANG INGIN DITAMPILKAN
# =========================================
available_months = sorted(filtered_df["Date"].unique())

selected_months = st.sidebar.multiselect(
    "Pilih Bulan yang Ditampilkan",
    options=available_months,
    default=available_months
)

filtered_df = filtered_df[
    filtered_df["Date"].isin(selected_months)
]

# Guard jika kosong
if filtered_df.empty:
    st.warning("Tidak ada data untuk bulan yang dipilih.")
    st.stop()

# ===============================
# AGGREGASI PER BULAN
# ===============================
agg_df = (
    filtered_df
    .groupby(["Date", "Category_Label"], as_index=False)
    .agg({"Shares": "sum"})
)

# ===============================
# BAR CHART PER BULAN
# ===============================
bar_chart = alt.Chart(agg_df).mark_bar().encode(
    x=alt.X(
        "yearmonth(Date):O",
        title="Bulan"
    ),
    y=alt.Y(
        "Shares:Q",
        title="Jumlah Saham"
    ),
    color=alt.Color(
        "Category_Label:N",
        title="Kategori Investor"
    ),
    tooltip=[
        "Category_Label:N",
        "Date:T",
        "Shares:Q"
    ]
).properties(
    height=520
)

st.altair_chart(bar_chart, use_container_width=True)
