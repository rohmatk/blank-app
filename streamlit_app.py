import streamlit as st
import altair as alt
import pandas as pd
import yfinance as yf
from datetime import timedelta

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
    page_title="Dashboard Kepemilikan & Harga Saham",
    layout="wide"
)

st.title("📊 Analisis Kepemilikan & Harga Saham (Equity Only)")

# ===============================
# LOAD & PREPARE OWNERSHIP DATA
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
# FETCH PRICE FROM YAHOO FINANCE
# ===============================
@st.cache_data(ttl=60 * 60)
def fetch_price_data(code, start_date, end_date):
    """
    Ambil harga saham dari Yahoo Finance
    dan ubah ke harga penutupan bulanan
    (flatten MultiIndex secara eksplisit)
    """
    try:
        ticker = f"{code}.JK"
        price = yf.download(
            ticker,
            start=start_date - timedelta(days=10),
            end=end_date + timedelta(days=5),
            progress=False
        )

        if price.empty:
            return None

        price = price.reset_index()
        price["Month"] = price["Date"].dt.to_period("M").dt.to_timestamp()

        monthly = (
            price
            .groupby("Month", as_index=False)
            .agg(Close=("Close", "last"))
            .rename(columns={"Month": "Date"})
        )

        monthly["Close"] = monthly["Close"].astype(float)

        return monthly

    except Exception:
        return None

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
agg_df = (
    code_df
    .groupby(["Date", "Category_Label"], as_index=False)
    .agg(
        Shares=("Shares", "sum"),
        NetFlow=("NetFlow", "sum")
    )
)

# ===============================
# TAMBAHAN KOLUMN VISUAL
# ===============================
agg_df["Direction"] = agg_df["NetFlow"].apply(
    lambda x: "Akumulasi" if x > 0 else "Distribusi"
)

agg_df["Magnitude"] = agg_df["NetFlow"].abs()

# ===============================
# AMBIL DATA HARGA
# ===============================
price_df = fetch_price_data(
    selected_code,
    start_date=agg_df["Date"].min(),
    end_date=agg_df["Date"].max()
)

# ===============================
# TAMPILKAN HARGA TERAKHIR
# ===============================
if price_df is not None and not price_df.empty:
    latest_price = float(
        price_df.sort_values("Date")["Close"].iloc[-1]
    )
    st.metric(
        label=f"Harga Penutupan Terakhir ({selected_code})",
        value=f"{latest_price:,.0f}"
    )
else:
    st.info("Harga saham tidak tersedia dari API.")

# ===============================
# CHART 1 — TOTAL KEPEMILIKAN
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
    y=alt.Y("NetFlow:Q", title="Perubahan Saham"),
    color=alt.Color(
        "Direction:N",
        scale=alt.Scale(
            domain=["Akumulasi", "Distribusi"],
            range=["#1b9e77", "#d95f02"]
        ),
        legend=alt.Legend(title="Arah")
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

zero_line = alt.Chart(
    pd.DataFrame({"y": [0]})
).mark_rule(color="black").encode(y="y:Q")

st.altair_chart(flow_chart + zero_line, use_container_width=True)

# ===============================
# CHART 3 — NET FLOW vs HARGA
# ===============================
if price_df is not None and not price_df.empty:

    flow_monthly = (
        agg_df
        .groupby("Date", as_index=False)["NetFlow"]
        .sum()
    )

    price_df = price_df.reset_index(drop=True)

    combined = pd.merge(
        flow_monthly,
        price_df,
        on="Date",
        how="inner"
    )

    flow_bar = alt.Chart(combined).mark_bar(opacity=0.4).encode(
        x="yearmonth(Date):O",
        y=alt.Y("NetFlow:Q", title="Net Flow")
    )

    price_line = alt.Chart(combined).mark_line(
        color="black",
        strokeWidth=3
    ).encode(
        x="yearmonth(Date):O",
        y=alt.Y("Close:Q", title="Harga Penutupan")
    )

    st.subheader("📈 Net Flow vs Harga Penutupan")
    st.altair_chart(
        alt.layer(flow_bar, price_line).resolve_scale(y="independent"),
        use_container_width=True
    )

# ===============================
# NARASI OTOMATIS
# ===============================
total_flow = agg_df["NetFlow"].sum()

dominant = (
    agg_df
    .groupby("Category_Label")["NetFlow"]
    .sum()
    .sort_values(ascending=False)
)

top_actor = dominant.index[0]
top_value = dominant.iloc[0]

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
