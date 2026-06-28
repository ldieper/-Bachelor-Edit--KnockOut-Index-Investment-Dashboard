import pandas as pd
from .df_functions import *
from classes.investment import Investment
from .plot_functions import filter_nearest_barriers

#Function fo running the investment simulation for all investments and returninng the dataframe
def run_simulation(source, filter, selected_leverage, selected_budget, remaining_budget, annual_cost):
    df = source.copy()
    
    # Convert to numpy arrays
    index_values = df["index_value"].values
    index_growth = df["index_growth"].values
    dates = df["date"].values

    rows = []
    investments_list = []
    investment_count = 0
    cumulative_value = 0

    #iterate through the dataframe (filter = starting 1 year after launch of index to rely on 52-week-high)
    for i in df[filter].index:

        #every month (20 trading days) the budget is being refilled
        if i % 20 == 0:
            remaining_budget += selected_budget

        #Creating new investment object
        if df.loc[i, "index_investpoint"]:
            
            investment_count += 1
            
            new_inv = Investment(
                index_values=index_values,
                index_growth=index_growth,
                dates=dates,
                i=i,
                selected_leverage=selected_leverage,
                selected_budget=selected_budget,
                remaining_budget=remaining_budget,
                inv_id=investment_count)
            investments_list.append(new_inv)
            new_inv.start_investment()
            if new_inv.active:
                remaining_budget -= new_inv.get_investment_value()
                cumulative_value += new_inv.get_investment_value()

        #iterating through all investments for checking status like knockout possibilities and setting values
        for inv in investments_list:

            if not inv.active:
                continue

            old_value = inv.get_investment_value()
            inv.update_current_knockout_barrier(i=i, annual_barrier_increase_pct = annual_cost)
            inv.update_investment_value(i=i)
            inv.update_leverage(i=i)
            inv.update_profit()
            new_value = inv.get_investment_value()
            cumulative_value += (new_value - old_value)

            #Knockout by leverage calculation (down -100% effectively)
            if inv.get_leverage() == 0:
                closing_value = inv.get_investment_value()
                inv.reset_investment(type="knockout")
                cumulative_value -= closing_value
                closing_date = dates[i]
                rows.append({
                    "date": dates[i],
                    "inv_id": inv.id,
                    "profit": inv.get_profit(),
                    "closing_reason": inv.closing_reason,
                    "starting_investment": inv.starting_investment,
                    "active": inv.active,
                    "cumulative_investment_value": cumulative_value,
                    "closing_date": closing_date,
                })
                continue

            #Knockout by index touching knockout_barrier
            if inv.get_investment_value() <= 0:
                closing_value = inv.get_investment_value()
                inv.reset_investment(type="knockout")
                cumulative_value -= closing_value
                closing_date = dates[i]
                rows.append({
                    "date": dates[i],
                    "inv_id": inv.id,
                    "profit": inv.get_profit(),
                    "closing_reason": inv.closing_reason,
                    "starting_investment": inv.starting_investment,
                    "active": inv.active,
                    "cumulative_investment_value": cumulative_value,
                    "closing_date": closing_date,
                })
                continue
            
            #Sell because effective leverage falls to  1.5 or below
            if inv.get_leverage() <= 1.5:
                closing_value = inv.get_investment_value()
                inv.reset_investment(type="sell")
                #cumulative_value -= closing_value
                closing_date = dates[i]
                rows.append({
                    "date": dates[i],
                    "inv_id": inv.id,
                    "profit": inv.get_profit(),
                    "closing_reason": inv.closing_reason,
                    "starting_investment": inv.starting_investment,
                    "active": inv.active,
                    "cumulative_investment_value": cumulative_value,
                    "closing_date": closing_date,
                })
                continue
            
            #Storing values in each investment
            rows.append({
                "date": dates[i],
                "inv_id": inv.id,
                "knockout_barrier": inv.get_current_knockout_barrier(),
                "current_value": inv.get_investment_value(),
                "leverage": inv.get_leverage(),
                "profit": inv.get_profit(),
                "closing_reason": inv.closing_reason,
                "starting_investment": inv.starting_investment,
                "active": inv.active,
                "cumulative_investment_value": cumulative_value,
                "starting_date": inv.starting_date,
                "closing_date": None,
            })
    df_investment = pd.DataFrame(rows)

    return remaining_budget, df_investment

#Running simulation for all possible indices and leverage options
def precompute_all_simulations(keys_to_compute=None, debug_index=None, debug_leverages=None, annual_cost=0.05): #debug_index="GDAXI", debug_leverages=3
    index_map = get_index_map()

    #Debug mode for especially returning specific inndex and leverage (also good for faster loaing times while fixing other bugs)
    if debug_index:
        index_map = {debug_index: index_map[debug_index]}
    leverages = [debug_leverages] if debug_leverages else [3, 5, 10]
    
    #Getting the wanted indices and leverages
    if keys_to_compute is None:
        keys_to_compute = {(index_name, leverage) for index_name in index_map.keys() for leverage in leverages}
    
    results = {}

    #Iterate for all indices and their possible leverages
    for index_name, leverage in keys_to_compute:
        if index_name not in index_map:
            continue
        file_path = index_map[index_name]
        df_all_index = load_df(file_path)
        if df_all_index is None or df_all_index.empty:
            print(f"Skipping index {index_name} because the data file is empty or invalid.")
            continue

        df_all_index, mask = prepare_investment_data(df_all_index)

        selected_budget = 500
        remaining_budget = selected_budget

        remaining_budget, df_investment = run_simulation(
            df_all_index,
            mask,
            leverage,
            selected_budget,
            remaining_budget,
            annual_cost  
        )

        df_simple_invest = run_simple_invests_simulation(
            df_all_index,
            selected_budget,
            expense_ratio=0.002, #0,2% of Shares = costs
            annual_dividend_yield=0.01, #1% dividend per Share
            allow_fractional=True)

        # Calculate metrics
        metrics = calculate_metrics(df_investment)

        df_investment_plot = df_investment[["date", "current_value", "inv_id", "knockout_barrier", "leverage", "profit", "cumulative_investment_value", "starting_date", "closing_date"]].drop_duplicates(subset=["date", "inv_id"], keep="last")
        
        #left join with df_all_index on mathing dates
        df_plot = pd.merge(
            df_all_index,
            df_investment_plot,
            on="date",
            how="left"
        )
        df_plot_filtered = filter_nearest_barriers(df_plot,top_n=1)
        
        barrier_growth = (
            df_investment[["inv_id", "date", "knockout_barrier"]]
            .dropna(subset=["knockout_barrier"])
            .groupby("inv_id")
            .agg(
                start_barrier=("knockout_barrier", "first"),
                end_barrier=("knockout_barrier", "last"),
                start_date=("date", "first"),
                end_date=("date", "last")
            )
            .reset_index()
        )
        barrier_growth["duration_days"] = (barrier_growth["end_date"] - barrier_growth["start_date"]).dt.days
        barrier_growth["annual_barrier_increase_pct"] = barrier_growth.apply(
            lambda row: round(((row["end_barrier"] / row["start_barrier"]) ** (365 / row["duration_days"]) - 1) * 100, 2)
            if row["duration_days"] > 0 and row["start_barrier"] > 0 else 0,
            axis=1
        )

        df_table = df_investment[df_investment["closing_reason"] != 2][["inv_id", "active", "closing_reason", "starting_date", "closing_date", "profit", "current_value", "starting_investment"]].copy()
        df_table = df_table.groupby("inv_id").last().reset_index(drop=False)
        df_table = df_table.merge(barrier_growth[["inv_id", "annual_barrier_increase_pct"]], on="inv_id", how="left")

        # Ensure `market_situation` exists on df_all_index to avoid KeyError
        if "market_situation" not in df_all_index.columns:
            df_all_index["market_situation"] = pd.NA

        # Map starting market situation. Keep `starting_date` as datetime for mapping,
        # then format it for display below.
        df_table["starting_market_situation"] = pd.to_datetime(df_table["starting_date"]).map(
            df_all_index.set_index("date")["market_situation"]
        )

        df_table["starting_date"] = df_table["starting_date"].dt.strftime("%d.%m.%y")
        df_table["closing_date"] = pd.to_datetime(df_table["closing_date"], errors='coerce').dt.strftime("%d.%m.%y")
        df_table["current_value"] = df_table["current_value"].where(df_table["active"], 0)
        df_table = df_table.sort_values(by=["inv_id"], ascending=True)

        cumulative_value = df_investment["cumulative_investment_value"].iloc[-1]

        #Storing values for each configuration
        key = (index_name, leverage)
        results[key] = {
            "df_all_index": df_all_index,
            "df_investment": df_investment,
            "df_table": df_table,
            "remaining_budget": remaining_budget,  
            "cumulative_value": cumulative_value,
            "metrics": metrics,
            "df_plot_filtered": df_plot_filtered,
            "knockout_barriers": barrier_growth,
            "df_simple_invest": df_simple_invest
        }

    return results

def run_simple_invests_simulation(source, monthly_budget, reinvest_pct=1.0, expense_ratio=0.02, annual_dividend_yield=0.01, allow_fractional=True):

    """
    Simulate a simple ETF savings plan (Sparplan) that:
    - invests `monthly_budget` every ~20 trading days
    - supports fractional shares with `allow_fractional`
    - supports "thesaurierend" reinvestment via `reinvest_pct` (0.0-1.0)
    - charges an annual `expense_ratio` (as decimal, e.g. 0.005 for 0.5%) applied pro-rata each trading day
    - optional `annual_dividend_yield` which is distributed monthly and partially reinvested

    Returns: df_simple_invest
    """

    df = source.copy()

    # Convert to numpy arrays
    index_values = df["index_value"].values
    dates = df["date"].values

    rows = []
    months_count = 0

    shares = 0.0  # number of shares held (float when fractional allowed)
    cash = 0.0   # cash leftover from buys and dividends
    total_invested = 0.0

    # assume ~252 trading days per year for expense/dividend pro-rata
    trading_days_per_year = 252

    for i in df.index:
        price = float(index_values[i])

        if i % 20 == 0:
            months_count += 1

            # dividends are distributed monthly on existing holdings
            if annual_dividend_yield and shares > 0:
                monthly_dividend = (annual_dividend_yield / 12.0) * (shares * price)
                reinvest_amount = monthly_dividend * float(reinvest_pct)
                cash += monthly_dividend - reinvest_amount

                if reinvest_amount > 0 and price > 0:
                    if allow_fractional:
                        shares += reinvest_amount / price
                    else:
                        shares_to_buy = int(reinvest_amount // price)
                        cost = shares_to_buy * price
                        if shares_to_buy > 0:
                            shares += shares_to_buy
                            cash += reinvest_amount - cost

            cash += monthly_budget

            # Buy shares with available cash
            if price > 0 and cash > 0:
                if allow_fractional:
                    shares_to_buy = cash / price
                    cost = shares_to_buy * price
                    shares += shares_to_buy
                    cash -= cost
                    total_invested += monthly_budget
                else:
                    shares_to_buy = int(cash // price)
                    cost = shares_to_buy * price
                    if shares_to_buy > 0:
                        shares += shares_to_buy
                        cash -= cost
                        total_invested += monthly_budget

        # daily expense fee based on current holdings value
        if expense_ratio and shares > 0:
            daily_fee = (expense_ratio / trading_days_per_year) * (shares * price)
            # charge fee from cash; allow cash to go negative rather than forcing a sale
            cash -= daily_fee

        total_value = shares * price + cash

        rows.append({
            "date": dates[i],
            "month_id": months_count,
            "shares": shares,
            "cash": cash,
            "price": price,
            "total_value": total_value,
            "total_invested": total_invested,
        })

    df_simple_invest = pd.DataFrame(rows)

    return df_simple_invest

