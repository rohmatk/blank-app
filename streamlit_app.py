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
def load_prepare() -> pd.DataFrame:
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
# AGREGASI BULANAN (LEVEL DULU)
# ===============================
agg_df = (
    code_df
    .groupby(["Date", "Category_Label"], as_index=False)
    .agg({"Shares": "sum"})
    .sort_values(["Category_Label", "Date"])
)

# ===============================
# HITUNG MoM (SETELAH AGREGASI)
# ===============================
agg_df["NetFlow"] = (
    agg_df
    .groupby("Category_Label")["Shares"]
    .diff()
    .fillna(0)
)

# ===============================
# KOLUMN VISUAL
# ===============================
agg_df["Direction"] = agg_df["NetFlow"].apply(
    lambda x: "Akumulasi" if x > 0 else "Distribusi" if x < 0 else "Stagnan"
)

agg_df["Magnitude"] = agg_df["NetFlow"].abs()

# ===============================
# CHART 1 — LEVEL KEPEMILIKAN
# ===============================
st.subheader("📦 Total Kepemilikan Saham")

level_chart = alt.Chart(agg_df).mark_bar().encode(
    x=alt.X("yearmonth(Date):O", title="Bulan"),
    y=alt.Y("Shares:Q", title="Jumlah Saham"),
    color=alt.Color("Category_Label:N", title="Kategori Investor"),
    tooltip=[
        "Category_Label",
        alt.Tooltip("Shares:Q", format=",")
    ]
).properties(height=420)

st.altair_chart(level_chart, use_container_width=True)

# ===============================
# CHART 2 — PERUBAHAN (MoM)
# ===============================
st.subheader("📉 Perubahan Kepemilikan (Month-over-Month)")

flow_chart = alt.Chart(agg_df).mark_bar().encode(
    x=alt.X("yearmonth(Date):O", title="Bulan"),
    y=alt.Y(
        "NetFlow:Q",
        title="Perubahan Saham",
        axis=alt.Axis(grid=True)
    ),
    color=alt.Color(
        "Direction:N",
        scale=alt.Scale(
            domain=["Akumulasi", "Distribusi", "Stagnan"],
            range=["#1b9e77", "#d95f02", "#999999"]
        ),
        legend=alt.Legend(title="Arah Perubahan")
    ),
    opacity=alt.Opacity(
        "Magnitude:Q",
        scale=alt.Scale(range=[0.3, 1.0]),
        legend=None
    ),
    tooltip=[
        "Category_Label",
        "Direction",
        alt.Tooltip("NetFlow:Q", format=",")
    ]
).properties(height=420)

# garis nol
zero_line = alt.Chart(
    pd.DataFrame({"y": [0]})
).mark_rule(color="black", strokeWidth=1).encode(y="y:Q")

st.altair_chart(flow_chart + zero_line, use_container_width=True)

# ===============================
# NARASI OTOMATIS
# ===============================
st.markdown("## 🧠 Ringkasan Otomatis")

total_flow = agg_df["NetFlow"].sum()

dominant = (
    agg_df
    .groupby("Category_Label")["NetFlow"]
    .sum()
    .sort_values(ascending=False)
)

top_actor = dominant.index[0]
top_value = dominant.iloc[0]
dominant_direction = "akumulasi" if top_value > 0 else "distribusi"

st.markdown(
    f"""
    Untuk saham **{selected_code}**, periode terpilih menunjukkan
    **{'akumulasi' if total_flow > 0 else 'distribusi' if total_flow < 0 else 'stagnan'} bersih**
    sebesar **{total_flow:,.0f} saham**.

    Perubahan paling dominan berasal dari
    **{top_actor}** dengan
    **{dominant_direction} sebesar {top_value:,.0f} saham**.
    """
)
