def melt_ownership(df):
    ownership_cols = [
        "Local IS","Local CP","Local PF","Local IB","Local ID",
        "Local MF","Local SC","Local FD","Local OT",
        "Foreign IS","Foreign CP","Foreign PF","Foreign IB","Foreign ID",
        "Foreign MF","Foreign SC","Foreign FD","Foreign OT"
    ]

    long_df = df.melt(
        id_vars=["Date", "Code"],
        value_vars=ownership_cols,
        var_name="Category",
        value_name="Shares"
    )

    return long_df
#