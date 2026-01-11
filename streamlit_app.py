import streamlit as st
import altair as alt
import pandas as pd

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

st.title("📊 Analisis Perubahan Kepemilikan Saham (Equity Only)")

# ===============================
# LOAD & PREPARE DATA
# ===============================
@st.cache_data
def load_prepare():
    raw_df = load_all_data()
    clean_df = clean_data(raw_df)
    long_df = melt_ownership(clean_df)
    long_df = map_investor_category(long_df)
    return long_df

df = load_prepare()

# ===============================
# SIDEBAR FILTER
# ===============================
st.sidebar.header("Filter Analisis")

selected_code = st.sidebar.selectbox(
    "Pilih Saham",
    sorted(df["Code"].unique())
)

code_df = df[df["Code"] == selected_code].copy()

# ===============================
# CATEGORY FILTER
# ===============================
available_categories = sorted(
    code_df["Category_Label"].dropna().unique()
)

categories = st.sidebar.multiselect(
    "Pilih Kategori Investor",
    options=available_categories,
    default=available_categories
)

code_df = code_df[
    code_df["Category_Label"].isin(categories)
]

# ===============================
# DATE FILTER
# ===============================
available_months = sorted(code_df["Date"].unique())

selected_months = st.sidebar.multiselect(
    "Pilih Bulan",
    options=available_months,
    default=available_months
)

code_df = code_df[
    code_df["Date"].isin(selected_months)
].copy()

if code_df.empty:
    st.warning("Tidak ada data untuk filter yang dipilih.")
    st.stop()

# ===============================
# HITUNG MoM NET FLOW
# ===============================
code_df = code_df.sort_values(
    ["Category_Label", "Date"]
)

code_df["NetFlow"] = (
    code_df
    .groupby("Category_Label")["Shares"]
    .diff()
    .fillna(0)
)

# ===============================
# AGGREGASI
# ===============================
agg_level = (
    code_df
    .groupby(["Date", "Category_Label"], as_index=False)
    .agg({
        "Shares": "sum",
        "NetFlow": "sum"
    })
)

# ===============================
# CHART 1 — LEVEL KEPEMILIKAN
# ===============================
st.subheader("📦 Total Kepemilikan Saham")

level_chart = alt.Chart(agg_level).mark_bar().encode(
    x=alt.X("yearmonth(Date):O", title="Bulan"),
    y=alt.Y("Shares:Q", title="Jumlah Saham"),
    color=alt.Color("Category_Label:N", title="Kategori"),
    tooltip=["Category_Label", "Shares"]
).properties(height=420)

st.altair_chart(level_chart, use_container_width=True)

# ===============================
# CHART 2 — PERUBAHAN (MoM)
# ===============================
st.subheader("📉 Perubahan Kepemilikan (Month-over-Month)")

flow_chart = alt.Chart(agg_level).mark_bar().encode(
    x=alt.X("yearmonth(Date):O", title="Bulan"),
    y=alt.Y("NetFlow:Q", title="Perubahan Saham"),
    color=alt.condition(
        alt.datum.NetFlow > 0,
        alt.value("#2ecc71"),
        alt.value("#e74c3c")
    ),
    tooltip=["Category_Label", "NetFlow"]
).properties(height=420)

st.altair_chart(flow_chart, use_container_width=True)

# ===============================
# NARASI OTOMATIS
# ===============================
total_flow = agg_level["NetFlow"].sum()

dominant_cat = (
    agg_level
    .groupby("Category_Label")["NetFlow"]
    .sum()
    .sort_values(ascending=False)
)

top_actor = dominant_cat.index[0]
top_value = dominant_cat.iloc[0]

st.markdown("## 🧠 Ringkasan Otomatis")

st.markdown(
    f"""
    Untuk saham **{selected_code}**, periode terpilih menunjukkan
    **{'akumulasi' if total_flow > 0 else 'distribusi'} bersih**
    sebesar **{total_flow:,.0f} saham**.

    Perubahan paling dominan berasal dari
    **{top_actor}** dengan kontribusi
    **{top_value:,.0f} saham**.
    """
)
