import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import yfinance as yf

# Loads the past 20 years of the chosen products and saves them once. (update for newer data must be done manually!)
def download_data(tickers=["^GDAXI", "^GSPC", "^HSI", "^STOXX50E", "EUNL.DE", "^SP500-35", "^SP500-40", "^SP500-45", "^YH103", "^YH206", "^YH311"]):
    #index: ^GDAXI = DAX, ^GSPC = S&P500, ^HSI = Hang Seng, ^STOXX50E = Euro Stoxx 50
    #EUNL.DE: iShares Core MSCI World UCITS ETF
    #Financial Services: ^SP500-40, ^YH103
    #HealthCare: ^SP500-35, ^YH206
    #Information Technology: ^SP500-45, ^YH311

    Path("index_data").mkdir(parents=True, exist_ok=True)

    for ticker in tickers:
        try:
            df = yf.download(ticker, period="20y", auto_adjust=False, progress=False)
            if df is None or df.empty:
                print(f"Warning: no data returned for {ticker}")
                continue

            df = df[["Close"]].copy()
            df.columns = ["index_value"]
            df.index.name = "date"
            df.to_parquet(f"index_data/{ticker}.parquet")
            print(f"Downloaded {ticker}: {df.shape[0]} rows")
        except Exception as error_message:
            print(f"Error downloading {ticker}: {error_message}")


# Updates the downloaded indices to the newest trading day (fills gap to old data)
def update_data(tickers=["^GDAXI", "^GSPC", "^HSI"]):
    for ticker in tickers:
        file_path = Path(f"index_data/{ticker}.parquet")
        if not file_path.exists():
            print(f"{ticker}: no data found → downloading 20y")
            download_data([ticker])
            continue

        try:
            old_df = pd.read_parquet(file_path)
            old_df.index = pd.to_datetime(old_df.index)
            last_date = old_df.index.max()
            start_date = last_date - timedelta(days=1)  # 1 Day because we need the closing data
            end_date = datetime.today()

            if start_date >= end_date:
                print(f"{ticker}: already up to date")
                continue

            print(f"{ticker}: updating from {start_date.date()} to {end_date.date()}")
            new_df = yf.download(
                ticker,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                auto_adjust=False,
                progress=False,
            )

            if new_df is None or new_df.empty:
                print(f"{ticker}: no new data")
                continue

            new_df = new_df[["Close"]].copy()
            new_df.columns = ["index_value"]
            new_df.index.name = "date"

            combined = pd.concat([old_df, new_df])
            combined = combined[~combined.index.duplicated(keep="last")]
            combined.to_parquet(file_path)
            print(f"{ticker}: update complete")
        except Exception as error_message:
            print(f"Error updating {ticker}: {error_message}")
