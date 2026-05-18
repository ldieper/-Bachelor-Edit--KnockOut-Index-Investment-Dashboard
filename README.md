# (Bachelor-Edit) KnockOut-Index-Investment-Dashboard

This **study project** is a Streamlit-based dashboard for simulating leveraged investments in major stock indices during market corrections. It allows users to explore how leveraged products would have performed when invested in downside phases and recovery periods.

The application is written in Python and currently supports simulations on DAX, FTSE 50, and S&P 500 indices, with stock Data starting in 2006. It provides an interactive interface to configure investment parameters and visualize key metrics. The index data is being stored as a .parquet file due to their time-series structure. For improved loading times a duckdb is being set up, which supports parquet by default and provides direct access to loaded simulations from previous sessions.

## Technology

- `streamlit`
- `duckdb`
- `python`
- `yfinance`

## Key features include

The main features of the dashboard are:

- **Simulation** of leveraged investment strategies over historical data
- **Interactive** plots showing portfolio performance over time
- **Key performance metrics** for evaluating investment outcomes
- **Detailed analysis** of individual investment periods

## Dashboard

![Preview](visuals/Dashboard_Demo.gif)

## The investment strategy in detail

### Capital Allocation

A fixed monthly contribution of €500 is added to the available cash balance.
The accumulated cash is held until an investment signal is triggered.
When conditions are met, 100% of the available cash is being invested into leveraged knockout products.

### Entry Conditions

An investment is initiated when the underlying index falls at least **10% below its 52-week high**, indicating a market correction.

### Position Sizing

Upon entry, the strategy purchases the maximum possible number of knockout products using the full available budget.
No partial allocation or diversification is applied; each position is fully capitalized.

### Investment Frequency

After opening a position, new investments are restricted.
A new position can only be opened after **20 trading days** (one investment period)
This constraint prevents overexposure during prolonged downturns.

### Exit Conditions

Positions are closed when the effective leverage falls below **1.5x**.
This typically reflects a recovery phase where the leveraged exposure diminishes.

### Profit Handling

Realized profits are not reinvested into future positions.
Only the ongoing monthly contributions (€500) are used to fund new investments.

## Installation and Dependencies

### Windows

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install streamlit pandas altair yfinance duckdb
```

### Linux / Mac

```bash
python -m venv .venv
source .venv/bin/activate
pip install streamlit pandas altair yfinance duckdb
```

## Technical structure

To start the dashboard execute:

```bash
streamlit run streamlit_app.py #alternative: python -m streamlit run app.py
```

The start of the dashboard follows following structure:

[Flowchart](visuals/flowchart.jpg)

Checking for the existence of the index data and database. Missing data is being downloaded and precomputed for display on the dashboard. Furthermore, the default settings are being applied.

## Additional resources

[Streamlit documentation](https://docs.streamlit.io/) <br>
[Yfinance documentation](https://ranaroussi.github.io/yfinance/)# -Bachelor-Edit--KnockOut-Index-Investment-Dashboard
