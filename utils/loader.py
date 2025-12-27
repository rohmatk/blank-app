import pandas as pd
import glob
import os

def load_all_data(data_folder="data"):
    files = glob.glob(os.path.join(data_folder, "*.txt"))
    df_list = []

    for file in files:
        df = pd.read_csv(file, sep="|")
        df.columns = df.columns.str.strip()
        df["SourceFile"] = os.path.basename(file)
        df_list.append(df)

    return pd.concat(df_list, ignore_index=True)
#