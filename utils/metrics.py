import pandas as pd

def net_flow(df):
    """
    Hitung perubahan kepemilikan bersih (MoM)
    """
    df = df.sort_values(["Code", "Category", "Date"])

    df["NetFlow"] = (
        df.groupby(["Code", "Category"])["Shares"]
          .diff()
          .fillna(0)
    )

    return df

def monthly_total_flow(df):
    return (
        df.groupby("Date")["NetFlow"]
          .sum()
          .reset_index(name="Market_NetFlow")
    )

def flow_ratio(df):
    df["Investor_Type"] = df["Category"].str.split().str[0]

    ratio = (
        df.groupby(["Date", "Investor_Type"])["NetFlow"]
          .sum()
          .reset_index()
          .pivot(index="Date", columns="Investor_Type", values="NetFlow")
          .fillna(0)
    )

    ratio["Foreign_Ratio"] = (
        ratio.get("Foreign", 0) /
        (ratio.get("Foreign", 0) + ratio.get("Local", 0)).replace(0, 1)
    )

    return ratio.reset_index()

def flow_acceleration(df):
    df["Acceleration"] = (
        df.groupby(["Code", "Category"])["NetFlow"]
          .diff()
          .fillna(0)
    )
    return df

def top_movers(df, date, n=10, direction="buy"):
    subset = df[df["Date"] == date]

    grouped = (
        subset.groupby("Code")["NetFlow"]
        .sum()
        .reset_index()
    )

    if direction == "buy":
        return grouped.sort_values("NetFlow", ascending=False).head(n)
    else:
        return grouped.sort_values("NetFlow").head(n)
