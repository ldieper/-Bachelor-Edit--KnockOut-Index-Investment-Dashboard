from pathlib import Path
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


# Loads the past 20years of the chosen products and saves them once. (update for newer data must be done manually!)
def download_data(tickers=["^GDAXI", "^GSPC", "^HSI", "^STOXX50E", "EUNL.DE", "ACWI.MI"]): #^GDAXI = DAX, ^GSPC = S&P500, ^HSI = Hang Seng Index; e.g. ^NDX = Nasdaq100, STOXX50E = EuroStoxx50 etc.
    for ticker in tickers:
        df = yf.download(
            ticker,
            period="20y",
            interval="1d",
            auto_adjust=True
        )

        # If no directory exists, create it
        Path("index_data").mkdir(parents=True, exist_ok=True)

        df = df[["Close"]]

        df.to_parquet(f"index_data/{ticker}.parquet")

        print(df.tail())

#Updates the downloaded indices to the newest trading day (fills gap to old data)
def update_data(tickers=["^GDAXI", "^GSPC", "^HSI"]):
    for ticker in tickers:
        file_path = Path(f"index_data/{ticker}.parquet")

        # If file doesn't exist → do full download
        if not file_path.exists():
            print(f"{ticker}: no data found → downloading 20y")
            download_data([ticker])
            continue

        # Load existing data
        old_df = pd.read_parquet(file_path)
        old_df.index = pd.to_datetime(old_df.index)

        last_date = old_df.index.max()

        # small overlap for safety (avoid missing corrections)
        start_date = last_date - timedelta(days=1) #1Day because we need the closing data
        end_date = datetime.today()

        if start_date >= end_date:
            print(f"{ticker}: already up to date")
            continue

        print(f"{ticker}: updating from {start_date.date()} to {end_date.date()}")

        # Download only missing data
        new_df = yf.download(
            ticker,
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            interval="1d",
            auto_adjust=True
        )

        if new_df.empty:
            print(f"{ticker}: no new data")
            continue

        new_df = new_df[["Close"]]

        # Merge old + new
        combined = pd.concat([old_df, new_df])
        combined = combined[~combined.index.duplicated(keep="last")]

        # Save as Parquet
        combined.to_parquet(file_path)

        print(f"{ticker}: update complete")
        print(combined.tail())