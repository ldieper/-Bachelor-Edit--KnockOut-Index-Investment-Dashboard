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
        (df_all_index["date"] >= "2015-05-01") & (df_all_index["date"] <= "2017-01-01"),
        (df_all_index["date"] >= "2020-01-01") & (df_all_index["date"] <= "2021-01-01"),
        (df_all_index["date"] >= "2022-02-14") & (df_all_index["date"] <= "2023-01-01"),
        (df_all_index["date"] >= "2023-03-01") & (df_all_index["date"] <= "2024-01-01"),
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
def calculate_metrics(df_investment, scope="Complete Timeline"):
    df_full = df_investment.sort_values("date")
    if df_full.empty:
        return {
            "scope": scope,
            "start_investment_level": 0,
            "end_investment_level": 0,
            "start_loss_sum": 0,
            "start_total_return": 0.0,
            "end_loss_sum": 0,
            "end_total_return": 0.0,
            "start_active_trades": 0,
            "start_closed_trades": 0,
            "end_active_trades": 0,
            "end_closed_trades": 0,
            "start_sells_count": 0,
            "start_knockouts_count": 0,
            "start_trades_count": 0,
            "end_sells_count": 0,
            "end_knockouts_count": 0,
            "end_trades_count": 0,
            "start_total_invested_sum": 0,
            "end_total_invested_sum": 0,
            "start_total_profit": 0,
            "end_total_profit": 0,
            "max_drawdown": None
        }

    # 1. Identify the bounds of the specific crisis scope
    if scope != "Complete Timeline":
        df_trades = df_full[df_full["market_situation"] == scope]
        if df_trades.empty:
            df_trades = df_full
        crisis_start = df_trades["date"].iloc[0]
        crisis_end = df_trades["date"].iloc[-1]
    else:
        df_trades = df_full
        crisis_start = df_full["date"].iloc[0]
        crisis_end = df_full["date"].iloc[-1]

    # 2. Get accurate portfolio investment levels at both markers
    start_state = df_trades[df_trades["date"] == crisis_start]
    end_state = df_trades[df_trades["date"] == crisis_end]

    start_investment_level = round(start_state["cumulative_investment_value"].iloc[0], 2) if not start_state.empty else 0
    end_investment_level = round(end_state["cumulative_investment_value"].iloc[-1], 2) if not end_state.empty else 0

    equity = df_trades["cumulative_investment_value"]

    max_drawdown = (
        round((((equity / equity.cummax()) - 1).min()) * 100, 2)
        if not equity.empty
        else None
    )

    trades_at_start = df_full[df_full["date"] <= crisis_start].groupby("inv_id").last()
    trades_at_start = trades_at_start[trades_at_start["closing_reason"] != 2] # Drop placeholders

    start_total_profit = round(trades_at_start["profit"].sum(), 2)
    start_total_invested_sum = round(trades_at_start["starting_investment"].sum(), 2)
    start_loss_sum = round(trades_at_start.loc[trades_at_start["closing_reason"] == 0, "starting_investment"].sum(), 2)
    start_total_return = round(start_total_profit / start_total_invested_sum * 100, 2) if start_total_invested_sum > 0 else 0.0

    start_active_trades = int(trades_at_start["active"].sum())
    start_closed_trades = int((~trades_at_start["active"].astype(bool)).sum())
    start_sells_count = int((trades_at_start["closing_reason"] == 1).sum())
    start_knockouts_count = int((trades_at_start["closing_reason"] == 0).sum())
    start_trades_count = len(trades_at_start)

    trades_at_end = df_full[df_full["date"] <= crisis_end].groupby("inv_id").last()
    trades_at_end = trades_at_end[trades_at_end["closing_reason"] != 2]

    end_total_profit = round(trades_at_end["profit"].sum(), 2)
    end_total_invested_sum = round(trades_at_end["starting_investment"].sum(), 2)
    end_loss_sum = round(trades_at_end.loc[trades_at_end["closing_reason"] == 0, "starting_investment"].sum(), 2)
    end_total_return = round(end_total_profit / end_total_invested_sum * 100, 2) if end_total_invested_sum > 0 else 0.0

    end_active_trades = int(trades_at_end["active"].sum())
    end_closed_trades = int((~trades_at_end["active"].astype(bool)).sum())
    end_sells_count = int((trades_at_end["closing_reason"] == 1).sum())
    end_knockouts_count = int((trades_at_end["closing_reason"] == 0).sum())
    end_trades_count = len(trades_at_end)

    return {
        "scope": scope,
        "start_investment_level": start_investment_level,
        "end_investment_level": end_investment_level,
        "start_loss_sum": start_loss_sum,
        "start_total_return": start_total_return,
        "end_loss_sum": end_loss_sum,
        "end_total_return": end_total_return,
        "start_active_trades": start_active_trades,
        "start_closed_trades": start_closed_trades,
        "end_active_trades": end_active_trades,
        "end_closed_trades": end_closed_trades,
        "start_sells_count": start_sells_count,
        "start_knockouts_count": start_knockouts_count,
        "start_trades_count": start_trades_count,
        "end_sells_count": end_sells_count,
        "end_knockouts_count": end_knockouts_count,
        "end_trades_count": end_trades_count,
        "start_total_invested_sum": start_total_invested_sum,
        "end_total_invested_sum": end_total_invested_sum,
        "start_total_profit": start_total_profit,
        "end_total_profit": end_total_profit, 
        "max_drawdown": max_drawdown 
    }

# Precompute metrics for all scopes
def calculate_all_scope_metrics(df_investment):
    """
    Precomputes metrics for all available scopes and returns a dictionary.
    This is called once during simulation precomputation and stored in results.
    """
    scopes = [
        "Complete Timeline",
        "World Financial Crisis",
        "Eurocrisis",
        "Chinese Stock Market Turbulence",
        "Covid-19 Pandemic",
        "Ukraine War Kickoff",
        "Banking Crisis",
        "US Trade War",
        "Iran War"
    ]
    
    scope_metrics = {}
    for scope in scopes:
        scope_metrics[scope] = calculate_metrics(df_investment, scope=scope)
    
    return scope_metrics

