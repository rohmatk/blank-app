import pandas as pd

# ===============================
# CLEAN DATA (EQUITY ONLY)
# ===============================
def clean_data(df):
    df.columns = df.columns.str.strip()

    # Filter hanya Equity
    df = df[df["Type"].str.upper().isin(["EQ", "EQUITY", "S"])].copy()

    # Date → datetime
    df["Date"] = pd.to_datetime(
        df["Date"],
        format="%d-%b-%Y",
        errors="coerce"
    )

    df = df.dropna(subset=["Date", "Code"])

    # Pastikan numerik
    non_numeric = ["Date", "Code", "Type", "SourceFile"]
    numeric_cols = [c for c in df.columns if c not in non_numeric]

    df[numeric_cols] = (
        df[numeric_cols]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
    )

    return df


# ===============================
# WIDE → LONG
# ===============================
def melt_ownership(df):
    ownership_cols = [
        "Local IS","Local CP","Local PF","Local IB","Local ID",
        "Local MF","Local SC","Local FD","Local OT",
        "Foreign IS","Foreign CP","Foreign PF","Foreign IB","Foreign ID",
        "Foreign MF","Foreign SC","Foreign FD","Foreign OT"
    ]

    ownership_cols = [c for c in ownership_cols if c in df.columns]

    return df.melt(
        id_vars=["Date", "Code"],
        value_vars=ownership_cols,
        var_name="Category",
        value_name="Shares"
    )


# ===============================
# MAP INVESTOR LABEL
# ===============================
def map_investor_category(long_df):
    investor_mapping = {
        'ID': 'Individual',
        'CP': 'Corporate (Perusahaan)',
        'MF': 'Mutual Fund (Reksa Dana)',
        'IB': 'Financial Institution (Lembaga Keuangan)',
        'IS': 'Insurance (Asuransi)',
        'SC': 'Securities Company (Perusahaan Efek)',
        'PF': 'Pension Fund (Dana Pensiun)',
        'FD': 'Foundation (Yayasan)',
        'OT': 'Others (Lainnya)'
    }

    def transform(cat):
        parts = cat.split()
        if len(parts) != 2:
            return cat
        region, code = parts
        return f"{region} {investor_mapping.get(code, code)}"

    long_df["Category_Label"] = long_df["Category"].apply(transform)

    return long_df
#