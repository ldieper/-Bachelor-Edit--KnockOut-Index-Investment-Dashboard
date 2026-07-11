import streamlit as st
import pandas as pd
import altair as alt
from functions.invest_sim_functions import *
from functions.df_functions import *
from functions.db_functions import *
from functions.plot_functions import *
from functions.trading_calendar_functions import *
from functions.loading_phrases_functions import *
from functions.yfinance_loader import *


st.set_page_config(layout="wide")


#Init
if get_index_map() == None:
    download_data()
index_map = get_index_map()

#Defaults for userinput variables
#if "refresh_data" not in st.session_state:
#    st.session_state.refresh_data = False

if "selected_index" not in st.session_state:
    if index_map:
        st.session_state.selected_index = list(index_map.keys())[0]
    else:
        st.session_state.selected_index = None

if "selected_leverage" not in st.session_state:
    st.session_state.selected_leverage = 3

if "simulations_loaded" not in st.session_state:
    st.session_state.simulations_loaded = False

if "all_results" not in st.session_state:
    st.session_state.all_results = None

if "selected_cost" not in st.session_state:
    st.session_state.selected_cost = 5

if "selected_scope" not in st.session_state:
    st.session_state.selected_scope = "Complete Timeline"




# Checking for completion of calculations and laoding of data
if st.session_state.selected_index is not None:
    if not st.session_state.simulations_loaded:
        st.session_state.all_results = load_from_db() #values from DB are being loaded into sesion_state
        expected_keys = {(index_name, leverage) for index_name in index_map.keys() for leverage in [3, 5, 10]}
        missing_keys = expected_keys - set(st.session_state.all_results.keys())

        if missing_keys: #Data from DB is not complete/empty -> New Data needs to be calculated
            with st.spinner("Precomputing.. " + get_random_phrase()):
                annual_cost = st.session_state.selected_cost / 100
                new_results = precompute_all_simulations(keys_to_compute=missing_keys, annual_cost=annual_cost, scope="st.session_state.selected_scope") #if db was empty: missing keys = all available keys
                store_to_db(new_results)
                st.session_state.all_results.update(new_results)
                st.cache_data.clear()
        st.session_state.simulations_loaded = True
        #st.rerun()


#Data-Refresh button clicked:
def data_refresh():
    # Reset flags/state
    st.session_state.simulations_loaded = False
    st.session_state.all_results = {}

    # Clear Streamlit caches
    st.cache_data.clear()
    st.cache_resource.clear()

    #Download and recompute Data
    update_data()
    expected_keys = {(index_name, leverage) for index_name in index_map.keys() for leverage in [3, 5, 10]}
    missing_keys = expected_keys - set(st.session_state.all_results.keys())

    #If not all indices are loaded
    if missing_keys:
        with st.spinner("Updating data.. "):
            annual_cost = st.session_state.selected_cost / 100
            new_results = precompute_all_simulations(keys_to_compute=missing_keys, annual_cost=annual_cost)
            st.session_state.all_results.update(new_results)    
            st.cache_data.clear()

    #st.session_state.refresh_data = False #Deactivating button to be cklickable again
    st.session_state.simulations_loaded = True


#If data is still not loaded: Error
if st.session_state.selected_index is None or st.session_state.all_results is None:
    st.error("Data not loaded properly. Selected index or results are missing.")
    st.stop()

selected_key = (st.session_state.selected_index, st.session_state.selected_leverage)
if selected_key not in st.session_state.all_results:
    st.error(
        f"No simulation results available for index {st.session_state.selected_index}. "
        "Please refresh data or remove empty/invalid index files."
    )
    st.stop()

#Storing calculations in current
current = st.session_state.all_results[selected_key] 


#assigning current values for all indices and leverage
df_all_index = current["df_all_index"]
df_investment = current["df_investment"]
df_plot_filtered = current["df_plot_filtered"]
remaining_budget = current["remaining_budget"]
cumulative_value = current["cumulative_value"]

# Get metrics for the selected scope
all_scope_metrics = current["metrics"]
metrics = all_scope_metrics.get(st.session_state.selected_scope, {})

# build summary table for all loaded combinations
summary_rows = []

for (index_name, leverage), result in st.session_state.all_results.items():

    result_all_scope_metrics = result.get("metrics", {})

    result_metrics = result_all_scope_metrics.get(
        st.session_state.selected_scope,
        {}
    )

    df_table = result.get("df_table")
    avg_barrier_increase = None
    if df_table is not None and not df_table.empty and "annual_barrier_increase_pct" in df_table.columns:
        avg_barrier_increase = round(df_table["annual_barrier_increase_pct"].dropna().mean(), 2)



    summary_rows.append({
        "Index": index_name,
        "Leverage": leverage,
        "Average Barrier Increase %": avg_barrier_increase,

        "Max Drawdown": result_metrics.get("max_drawdown"),

        "start_investment_level": result_metrics.get("start_investment_level"),
        "end_investment_level": result_metrics.get("end_investment_level"),
        "diff_investment_level": round(result_metrics.get("end_investment_level") - result_metrics.get("start_investment_level"), 2),
        
        "start_loss_sum": result_metrics.get("start_loss_sum"),
        "end_loss_sum": result_metrics.get("end_loss_sum"),
        "diff_loss_sum": round(result_metrics.get("end_loss_sum") - result_metrics.get("start_loss_sum"), 2),

        "start_total_invested_sum": result_metrics.get("start_total_invested_sum"),
        "end_total_invested_sum": result_metrics.get("end_total_invested_sum"),
        "diff_total_invested_sum": round(result_metrics.get("end_total_invested_sum") - result_metrics.get("start_total_invested_sum"), 2),

        "start_total_return": result_metrics.get("start_total_return"), 
        "end_total_return": result_metrics.get("end_total_return"),
        "diff_total_return": round((result_metrics.get("end_total_return") - result_metrics.get("start_total_return")), 2),

        "start_total_profit" : result_metrics.get("start_total_profit"),
        "end_total_profit" : result_metrics.get("end_total_profit"),
        "diff_total_profit" : round(result_metrics.get("end_total_profit") - result_metrics.get("start_total_profit"), 2),
        
        "start_active_trades": result_metrics.get("start_active_trades"),
        "end_active_trades": result_metrics.get("end_active_trades"),
        "diff_active_trades": result_metrics.get("end_active_trades") - result_metrics.get("start_active_trades"),

        "start_closed_trades": result_metrics.get("start_closed_trades"),
        "end_closed_trades": result_metrics.get("end_closed_trades"),
        "diff_closed_trades": result_metrics.get("end_closed_trades") - result_metrics.get("start_closed_trades"),
        
        "start_sells_count": result_metrics.get("start_sells_count"),
        "end_sells_count": result_metrics.get("end_sells_count"),
        "diff_sells_count": result_metrics.get("end_sells_count") - result_metrics.get("start_sells_count"),

        "start_knockouts_count": result_metrics.get("start_knockouts_count"),
        "end_knockouts_count": result_metrics.get("end_knockouts_count"),
        "diff_knockouts_count": result_metrics.get("end_knockouts_count") - result_metrics.get("start_knockouts_count"),

        "start_trades_count": result_metrics.get("start_trades_count"),
        "end_trades_count": result_metrics.get("end_trades_count"),
        "started_investments": result_metrics.get("started_investments")

    })

summary_df = pd.DataFrame(summary_rows)
summary_df.columns = (
    summary_df.columns
    .str.replace("_", "")
    .str.replace(" ", "")
    .str.replace("%", "pct")
)
if not summary_df.empty:
    summary_df = summary_df.sort_values(["Index", "Leverage"]).reset_index(drop=True)





df_simple_invest = current.get("df_simple_invest")
if df_simple_invest is None or (hasattr(df_simple_invest, 'empty') and df_simple_invest.empty):
    df_simple_invest = run_simple_invests_simulation(
        df_all_index,
        500,
        expense_ratio=0.002,
        annual_dividend_yield=0.01,
        allow_fractional=True
    )

# prepare a simple plot dataset for the simple investment section
if df_simple_invest is not None and "date" in df_simple_invest.columns and not df_simple_invest.empty:
    df_simple_invest = df_simple_invest.copy()

    if "market_situation" not in df_simple_invest.columns:
        df_simple_invest = df_simple_invest.merge(
            df_all_index[["date", "market_situation"]],
            on="date",
            how="left"
        )

    if st.session_state.selected_scope != "Complete Timeline":
        scope_mask = df_all_index["market_situation"] == st.session_state.selected_scope
        if scope_mask.any():
            scope_dates = df_all_index.loc[scope_mask, "date"]
            start_date = scope_dates.iloc[0]
            end_date = scope_dates.iloc[-1]
            df_simple_invest = df_simple_invest.loc[
                (df_simple_invest["date"] >= start_date) &
                (df_simple_invest["date"] <= end_date)
            ].copy()
            df_plot_index_scope = df_all_index.loc[
                (df_all_index["date"] >= start_date) &
                (df_all_index["date"] <= end_date),
                ["date", "index_value"]
            ].copy()
        else:
            df_plot_index_scope = df_all_index[["date", "index_value"]].copy()
    else:
        df_plot_index_scope = df_all_index[["date", "index_value"]].copy()

    if "profit" not in df_simple_invest.columns:
        df_simple_invest["profit"] = df_simple_invest["total_value"] - df_simple_invest["total_invested"]

    if "roi_percent" not in df_simple_invest.columns:
        df_simple_invest["roi_percent"] = df_simple_invest.apply(
            lambda row: round((row["profit"] / row["total_invested"]) * 100, 2)
            if row["total_invested"] else 0,
            axis=1,
        )

    if df_simple_invest is not None and not df_simple_invest.empty:
        df_plot_simple_invest = pd.merge(
            df_plot_index_scope,
            df_simple_invest[["date", "total_value"]],
            on="date",
            how="left"
        )
    else:
        df_plot_simple_invest = df_plot_index_scope.copy()
else:
    df_plot_simple_invest = df_all_index[["date", "index_value"]].copy()

#Dynamic Header (historic or up to date)
last_trading_day = get_last_trading_day().date()
df_last_day = get_last_investment_day(df_all_index).date()

if df_last_day < last_trading_day:
    st.header(f"KnockOut-Investments on indices (historic)")
else:
    st.header(f"KnockOut-Investments on indices")


#Layout / UI
top = st.container(border=True)
mid = st.container(border=True)
bottom = st.container(border=True)


with top:

    #css for metric buttons (Border on Hover) | Not needed, only aesthetic use
    st.markdown("""
    <style>

    div[data-testid="stMetric"] {
        padding: 12px;
        border: 2px solid transparent;
        border-radius: 14px;
        /* box-shadow: 0 2px 10px rgba(0,0,0,0.08); */
        transition: all 0.2s ease;
    }

    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px) scale(1.02);
        border: 2px solid #3D4044;
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }

    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="blue-section">', unsafe_allow_html=True)



    st.subheader(f"Index performance - {st.session_state.selected_index}")

    #Offset of Legend to be in top left corner
    legend = alt.Legend(
        orient="none",
        legendX=10,
        legendY=10
    )

    df = df_all_index.sort_values("date")

    df_bg = df[df["market_situation"].notna()].copy()
    df_bg["period_id"] = (df_bg["market_situation"] != df_bg["market_situation"].shift()).cumsum()
    df_periods = (
        df_bg
        .groupby(["period_id", "market_situation"], as_index=False)
        .agg(start=("date", "first"), end=("date", "last"))
    )

    df_inv = df_investment.copy()
    df_inv["market_situation"] = None

    for _, row in df_periods.iterrows():
        mask = (
            (df_inv["date"] >= row["start"]) &
            (df_inv["date"] <= row["end"])
        )

        df_inv.loc[mask, "market_situation"] = row["market_situation"]


    if st.session_state.selected_scope == "Complete Timeline":
        df_plot = df_plot_filtered
        df_inv = df_investment
        df_periods_plot = df_periods

    else:
        df_plot = df_plot_filtered[
            df_plot_filtered["market_situation"] == st.session_state.selected_scope
        ]

        df_inv = df_inv = df_inv[
            df_inv["market_situation"].eq(st.session_state.selected_scope)
        ].copy()
        

        df_periods_plot = df_periods[
            df_periods["market_situation"] == st.session_state.selected_scope
        ]


    #Base chart
    base = alt.Chart(df_plot).encode(
        x=alt.X("date:T", title="Datum", axis=alt.Axis(format="%d %b %y"))
    )

    #Group for the indipendent left axis ł
    left_axis_group = alt.layer(
        base.transform_calculate(lines="'Index'").mark_line().encode(
            y=alt.Y("index_value:Q", title="Index & Barrier Level"),
            color=alt.Color("lines:N", legend=legend,
                            scale=alt.Scale(domain=["Index", "Barrier", "Investment"],
                                            range=["#BA2BAC", "#c4265e", "#e2e22e"]))
        ),

        base.transform_calculate(lines="'Barrier'").mark_line().encode(
            y="knockout_barrier:Q",
            detail="inv_id:N",
            color=alt.Color("lines:N", legend=None)
        )
    )

    #Group for the indipendent right axis
    right_axis_group = alt.Chart(df_inv).transform_calculate(
        lines="'Investment'"
    ).mark_line(size=2).encode(
        x="date:T", 
        y=alt.Y("cumulative_investment_value:Q", title="Investment Value (€)"),
        color=alt.Color(
            "lines:N",
            scale=alt.Scale(
                domain=["Investment"],
                range=["#e2e22e"]
            ),
            legend=None
        )
    )


    period_bg = alt.Chart(df_periods_plot).mark_rect(opacity=0.1).encode(
        x="start:T",
        x2="end:T",
        y=alt.value(0),
        y2=alt.value(400),
        color=alt.Color(
            "market_situation:N",
            scale=alt.Scale(
                domain=[
                    "World Financial Crisis",
                    "Eurocrisis",
                    "Chinese Stock Market Turbulence",
                    "Covid-19 Pandemic",
                    "Ukraine War Kickoff",
                    "Banking Crisis",
                    "US Trade War",
                    "Iran War"
                ],
                range=[
                    "#23b172",
                    "#ff0000ff",
                    "#23b172",
                    "#ff0000ff",
                    "#23b172",
                    "#ff0000ff",
                    "#23b172",
                    "#ff0000ff"
                ]
            ),
            legend=None
        )
    )

    #Combining Charts to be displayed as one
    combined_chart = alt.layer(
        period_bg,
        left_axis_group,
        right_axis_group
    ).resolve_scale(
        y="independent",
        color="independent"
    ).properties(height=420)

    st.altair_chart(combined_chart, width="stretch")


    top_left, top_mid, top_right = st.columns([0.35, 0.35, 0.3])

    #Metrics of total investment
    with top_left:

        with st.container(border=True):

            st.subheader("Starting metrics")

            col1, col2 = st.columns(2)

            start_trades = metrics["start_trades_count"]
            end_trades = metrics["end_trades_count"]

            with col1:

                st.metric(
                    "Portfolio Value (Start)",  
                    f"€ {metrics['start_investment_level']:,.2f}".replace(",", " ")
                )

                st.metric(
                    "Invested Capital (Start)",
                    f"€ {metrics['start_total_invested_sum']:,.2f}".replace(",", " ")
                )

                st.metric(
                    "ROI (Start)",
                    f"{metrics['start_total_return']} %" if metrics['start_total_return'] is not None else "N/A"
                )

                st.metric(
                    "Max Drawdown",
                    f"{metrics.get('max_drawdown')} %"
                    if metrics.get("max_drawdown") is not None else "N/A"
                )
                
                st.metric(
                    "Profit (Start)",
                    f"€ {metrics['start_total_profit']:,.2f}".replace(",", " ")
                )


            with col2:

                st.metric (
                    "Trades (Start)",
                    f"{start_trades}"
                )

                st.metric(
                    "Knockouts (Start)",
                    f"{metrics['start_knockouts_count']}"
                )

                st.metric(
                    "Sells (Start)",
                    f"{metrics['start_sells_count']}"
                )

                st.metric(
                    "Active Positions (Start)",
                    f"{metrics['start_active_trades']}"
                )

                st.metric(
                    "Losses (Start)",
                    f"€ {metrics['start_loss_sum']:,.2f}".replace(",", " ")
                )

    with top_mid:

        with st.container(border=True):

            st.subheader("End metrics")

            col1, col2 = st.columns(2)

            with col1:

                st.metric(
                    "Portfolio Value (End)",
                    f"€ {metrics['end_investment_level']:,.2f}".replace(",", " "),
                    f"{round((metrics['end_investment_level'] - metrics['start_investment_level']) / metrics['start_investment_level'] * 100 if metrics['start_investment_level'] else 0, 2)} %"
                )

                st.metric(
                    "Invested Capital (End)",
                    f"€ {metrics['end_total_invested_sum']:,.2f}".replace(",", " "),
                    f"€ {round(metrics['end_total_invested_sum'] - metrics['start_total_invested_sum']) }"
                )

                st.metric(
                    "ROI (End)",
                    f"{metrics['end_total_return']} %" if metrics['end_total_return'] is not None else "N/A",
                    f"{round(metrics['end_total_return'] - metrics['start_total_return'], 2) } %"
                )

                st.metric(
                    "Max Drawdown",
                    f"{metrics.get('max_drawdown')} %"
                    if metrics.get("max_drawdown") is not None else "N/A"
                )

                st.metric(
                    "Profit (End)",
                    f"€ {metrics['end_total_profit']:,.2f}".replace(",", " "),
                    f"€ {round(metrics['end_total_profit'] - metrics['start_total_profit']) }"
                )


            with col2:

                st.metric (
                    "Trades (End)",
                    f"{end_trades}",
                    f"{(end_trades - start_trades)}"
                )

                st.metric(
                    "Knockouts (End)",
                    f"{metrics['end_knockouts_count']}",
                    f"{metrics['end_knockouts_count'] - metrics['start_knockouts_count']}",
                    delta_color="inverse"
                )

                st.metric(
                    "Sells (End)",
                    f"{metrics['end_sells_count']}",
                    f"{metrics['end_sells_count'] - metrics['start_sells_count']}"  
                )

                st.metric(
                    "Active Positions (End)",
                    f"{metrics['end_active_trades']}",
                    f"{metrics['end_active_trades'] - metrics['start_active_trades']}"
                )

                st.metric(
                    "Losses (End)",
                    f"€ {metrics['end_loss_sum']:,.2f}".replace(",", " "),
                    f"€ {metrics['end_loss_sum'] - metrics['start_loss_sum']:,.2f}",
                    delta_color="inverse"
                )

    #Settings for Dashboard
    with top_right:

        with st.container(border=True):

            st.subheader("Settings")

            col1, col2 , col3 = st.columns(3)

            index_map = get_index_map()

            with col1:
                st.radio(
                    "Index",
                    list(index_map.keys()),
                    key="selected_index"
                )

            with col2:
                st.radio(
                    "Leverage",
                    [3, 5, 10],
                    key="selected_leverage"
                )
            with col3:
                st.radio(
                    "annual_KO_cost in %",
                    [2, 3, 4, 5, 6, 7],
                    index=5,
                    key="selected_cost",
                    on_change=data_refresh
                )

        with st.container(border=False):
            if st.button("Refresh Data"):
                #st.session_state.refresh_data = True
                data_refresh()

    top_left, top_right = st.columns([0.2, 0.8])

    with top_left:
        with st.container(border=True):
            st.subheader("Scope")

            st.radio(
                "Market Situation",
                ["Complete Timeline",
                 "World Financial Crisis",
                 "Eurocrisis",
                 "Chinese Stock Market Turbulence",
                 "Covid-19 Pandemic",
                 "Ukraine War Kickoff",
                 "Banking Crisis",
                 "US Trade War",
                 "Iran War"],
                key="selected_scope"
            )

    with top_right:
        if not summary_df.empty:
            with st.container(border=True):
                st.subheader("All combinations summary")
                st.dataframe(summary_df, width="stretch")

    st.markdown('</div>', unsafe_allow_html=True)


#Metrics and settings
with mid:

    #Dispplay of the simple, monthly invest in the same selected_index
    st.subheader(f"Simple performance - {st.session_state.selected_index}")

    #Offset of Legend to be in top left corner
    legend = alt.Legend(
        orient="none",
        legendX=10,
        legendY=10
    )

    #Base chart
    base = alt.Chart(df_plot_simple_invest).encode(
        x=alt.X("date:T", title="Datum", axis=alt.Axis(format="%d %b %y"))
    )

    #Plot index value on the left axis
    left_axis_group = base.mark_line().encode(
        y=alt.Y("index_value:Q", title="Index value"),
        color=alt.value("#BA2BAC")
    )

    #Plot simple investment portfolio value on the right axis
    right_axis_group = alt.Chart(df_simple_invest).transform_calculate(
        lines="'Investment'"
    ).mark_line(size=2, color="#e2e22e").encode(
        x="date:T",
        y=alt.Y("total_value:Q", title="Portfolio Value (€)"),
        tooltip=["date:T", "total_value:Q"]
    )

    #Combining Charts to be displayed as one
    combined_chart = alt.layer(
        left_axis_group,
        right_axis_group
    ).resolve_scale(
        y="independent"
    )

    st.altair_chart(combined_chart, width="stretch")


    mid_left, mid_right = st.columns([0.7, 0.3])

    with mid_left:

        if df_simple_invest is not None and not df_simple_invest.empty:
            total_months = df_simple_invest["month_id"].iloc[-1]
            final_row = df_simple_invest.iloc[-1]
        else:
            total_months = 0
            final_row = pd.Series({"total_invested": 0, "total_value": 0})

        total_invested = final_row["total_invested"]
        final_value = final_row["total_value"]
        profit = final_value - total_invested
        roi_percent = (profit / total_invested) * 100 if total_invested > 0 else 0

        if st.session_state.selected_scope != "Complete Timeline":
            scope_dates = df_all_index[df_all_index["market_situation"] == st.session_state.selected_scope]["date"]
            if not scope_dates.empty:
                scope_start = scope_dates.iloc[0]
                scope_end = scope_dates.iloc[-1]
                df_simple_scope = df_simple_invest[
                    (df_simple_invest["date"] >= scope_start) &
                    (df_simple_invest["date"] <= scope_end)
                ].copy() if df_simple_invest is not None and not df_simple_invest.empty else pd.DataFrame()
                if not df_simple_invest.empty:
                    start_date = df_simple_invest["date"].min()
                    end_date = df_simple_invest["date"].max()

                    start_row = df_simple_invest[df_simple_invest["date"] == start_date].iloc[0]
                    end_row = df_simple_invest[df_simple_invest["date"] == end_date].iloc[0]

                    start_value = start_row["total_value"]
                    end_value = end_row["total_value"]
                    start_invested = start_row["total_invested"]
                    end_invested = end_row["total_invested"]

                    roi_start = ((start_value - start_invested) / start_invested * 100) if start_invested else 0
                    roi_end = ((end_value - end_invested) / end_invested * 100) if end_invested else 0

        
            col11, col22 = st.columns(2)

            with col11:
                with st.container(border=True):
                    st.subheader("Start Metrics of simple investment")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Investment-Level (Start)", f"€ {round(start_invested, 2):,.2f}".replace(",", " "))
                    
                    with col2:
                        st.metric("ROI (Start)", f"{roi_start:.2f} %")

            with col22:
                with st.container(border=True):
                    st.subheader("End Metrics of simple investment")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Investment-Level (End)", f"€ {round(end_invested, 2):,.2f}".replace(",", " "))
                        
                    with col2:
                        st.metric("ROI (End)", f"{roi_end:.2f} %")


        with st.container(border=True):
            st.subheader("Final simple investment summary")
            if df_simple_invest is not None and not df_simple_invest.empty:
                final_summary = pd.DataFrame([final_row])
                if "date" in final_summary.columns:
                    final_summary["date"] = pd.to_datetime(final_summary["date"]).dt.strftime("%Y-%m-%d")
                st.dataframe(
                    final_summary[["total_invested", "total_value", "profit", "roi_percent"]],
                    width="stretch",
                    hide_index=True
                )
            else:
                st.info("No simple investment data available.")


#Metrics of individual investments
with bottom:

    bottom_left, bottom_right = st.columns([0.12, 0.88])

    df_filtered = current["df_table"]

    with bottom_left:
        st.subheader("Investments")

        #For better readability
        closing_reason_map = {0.0: "KnockOut", 1.0: "Sold", 2.0: "No Money", None: "Active"}

        # Add mapped closing_reason column to display
        df_display = df_filtered.copy()
        df_display["closing_reason"] = df_display["closing_reason"].apply(
            lambda x: closing_reason_map.get(float(x), "Unbekannt") if pd.notna(x) else "Aktiv"
        )


        #Table to click on all possible investments of choosen index
        event = st.dataframe(
            df_display[["inv_id", "closing_reason", "annual_barrier_increase_pct"]],
            hide_index=True,
            width="stretch",
            on_select="rerun",
            selection_mode="single-row"
        )

        #Handling selected investment of table
        selected_row = None
        if event.selection.rows:
            selected_row = event.selection.rows[0]
        else:
            selected_row = 0 if len(df_filtered) > 0 else None  # Default: 1st row

    #View and metrics of choosen investment
    with bottom_right:
        st.subheader("Detailed view of Investments")

        if selected_row is not None and selected_row < len(df_filtered):
            selected_inv_id = df_filtered.iloc[selected_row]['inv_id']



            # Create and display the investment detail chart
            detail_chart = create_investment_detail_plot(df_investment, df_all_index, selected_inv_id)
            if detail_chart:
                st.altair_chart(detail_chart, width="stretch")

            selected_row_data = df_filtered.iloc[selected_row]

            avg_annual_barrier_increase = selected_row_data.get('annual_barrier_increase_pct', 0)

            # Map closing reason to readable text
            closing_reason_value = selected_row_data['closing_reason']
            if closing_reason_value is None or pd.isna(closing_reason_value):
                closing_reason_text = "Active"
            else:
                closing_reason_text = closing_reason_map.get(float(closing_reason_value), "Unknown")


            col1, col2, col3 ,col4, col5, col6 = st.columns(6)

            # Metrics
            with col1:
                starting_date = selected_row_data['starting_date']
                st.metric("Start", f"{starting_date}")

                st.metric("Avg. Annual Barrier Increase", f"{avg_annual_barrier_increase:.2f} %")

            with col2:
                start_investment = round(
                    selected_row_data.get('start_investment', selected_row_data.get('starting_investment', 0)),
                    2,
                )

            with col3:
                if selected_row_data['active']:
                    current_value = selected_row_data['current_value']
                    st.metric("Current Value", f"€ {current_value:,.2f}".replace(",", " "))

                elif not selected_row_data['active']:
                    closing_date = selected_row_data['closing_date']
                    st.metric("End", f" {closing_date}")

            with col4:
                start_regime = selected_row_data.get('Start regime') or selected_row_data.get('starting_market_situation')
                st.metric("Start regime", f"{start_regime}")

            with col5:
                st.metric("Status", closing_reason_text)

            with col6:
                profit_value = selected_row_data['profit']
                st.metric("Profit", f"€ {profit_value:,.2f}".replace(",", " "))

            with col6:
                indiv_return = round(((profit_value / start_investment if start_investment != 0 else 0) * 100), 2)
                st.metric("ROI", f"{indiv_return} %")

        else:
            st.info("Choose an investment from the table")



