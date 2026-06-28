import pandas as pd
from pathlib import Path
from .yfinance_loader import *
import numpy as np

#Map of the downloaded indices
def get_index_map(folder="index_data"):
    index_map = {}

    if not any(Path(folder).glob("*.parquet")):
        print(f"No Parquet files found in {folder}, downloading data...")
        return None

    for file in Path(folder).glob("*.parquet"):
        # Use filename (without extension) as default name
        name = file.stem
        
        name = name.replace("^", "")  # remove ^ if present
        
        index_map[name] = str(file)
    
    return index_map


#Load the downlaoded dataframes
def load_df(file_path):

    try:
        df = pd.read_parquet(file_path)
        df.columns = ["index_value"]
        df.index.name = "date"
        df = df.reset_index()
        if df.empty:
            print(f"Warning: loaded parquet {file_path} is empty")
            return pd.DataFrame(columns=["date", "index_value"])
        return df

    #Catching exception
    except Exception as error_message:
        print(f"Error loading Parquet: {error_message}")
        return None


#Setting the investmentpoints in the dataframe
def prepare_investment_data(df_all_index):
    if df_all_index is None or df_all_index.empty:
        df_all_index = pd.DataFrame(columns=["date", "index_value", "index_growth", "index_investpoint", "yearly_high"])
        return df_all_index, pd.Series(False, index=df_all_index.index)

    df_all_index["index_growth"] = df_all_index["index_value"].pct_change().fillna(0)
    
    df_all_index["index_investpoint"] = None

    #52-week-high (rolling for every day)
    df_all_index["yearly_high"] = (
        df_all_index["index_value"]
            .rolling(window=252, min_periods=1)  # ~252 Trading Days = 1 Year
            .max()
    )

    start_date = df_all_index["date"].iloc[0] + pd.DateOffset(years=1) #Starts one year in, so the 52-week high can be used as reference point
    mask = df_all_index["date"] > start_date

    # Adding investmentpoints 
    for i in df_all_index[mask].index:
        price = df_all_index.loc[i, "index_value"]
        high = df_all_index.loc[i, "yearly_high"]

        if df_all_index["index_investpoint"].sum() == 0:
            if price < high * 0.9:
                df_all_index.loc[i, "index_investpoint"] = True
                continue

        if price < high * 0.9:
            if not df_all_index["index_investpoint"].iloc[max(0, i-20):i].any():
                df_all_index.loc[i, "index_investpoint"] = True
                continue

    df_all_index["market_situation"] = np.select(
        [
            (df_all_index["date"] >= "2007-08-09") & (df_all_index["date"] <= "2009-08-09"),
            (df_all_index["date"] >= "2010-01-01") & (df_all_index["date"] <= "2015-01-01"),
            (df_all_index["date"] >= "2015-01-01") & (df_all_index["date"] <= "2017-01-01"),
            (df_all_index["date"] >= "2020-01-01") & (df_all_index["date"] <= "2021-01-01"),
            (df_all_index["date"] >= "2022-02-14") & (df_all_index["date"] <= "2023-01-01"),
            (df_all_index["date"] >= "2023-05-01") & (df_all_index["date"] <= "2024-01-01"),
            (df_all_index["date"] >= "2025-03-01") & (df_all_index["date"] <= "2025-05-01"),
            (df_all_index["date"] >= "2026-02-28") & (df_all_index["date"] <= "2026-05-01"),
        ],
        [
            "World Financial Crisis",
            "Eurocrisis",
            "Chinese Stock Market Turbulence",
            "Covid-19 Pandemic",
            "Ukraine War Kickoff",
            "Banking Crisis",
            "US Trade War",
            "Iran War"
        ],
        default=None
    )

    return df_all_index, mask

#Calculating metrics and returning them as one
def calculate_metrics(df_investment):
    final_trades = df_investment.groupby("inv_id").last()

    active_trades = final_trades["active"].sum()

    closed_trades = (~final_trades["active"]).sum()
    sells_count = (final_trades["closing_reason"] == 1).sum()
    knockouts_count = (final_trades["closing_reason"] == 0).sum()

    trades_count = (final_trades["closing_reason"] != 2).sum()
    knockouts_count = (final_trades["closing_reason"] == 0).sum()
    sells_count = (final_trades["closing_reason"] == 1).sum()
    not_enough_money_count = (final_trades["closing_reason"] == 2).sum()
    active_trades = final_trades["active"].sum()

    final_profit = round(final_trades["profit"].sum(), 2)
    loss_sum = round(final_trades.loc[final_trades["closing_reason"] == 0, "starting_investment"].sum(), 2)
    total_invested_sum = round(final_trades.loc[final_trades["closing_reason"] != 2, "starting_investment"].sum(), 2)

    total_return = round(final_profit / total_invested_sum * 100, 2) if total_invested_sum > 0 else 0

    

    return {
        "closed_trades": closed_trades,
        "sells_count": sells_count,
        "knockouts_count": knockouts_count,
        "not_enough_money_count": not_enough_money_count,
        "final_profit": final_profit,
        "trades_count": trades_count,
        "active_trades": active_trades,
        "loss_sum": loss_sum,
        "total_invested_sum": total_invested_sum,
        "total_return": total_return,
    }

