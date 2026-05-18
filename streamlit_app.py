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




# Checking for completion of calculations and laoding of data
if st.session_state.selected_index is not None:
    if not st.session_state.simulations_loaded:
        st.session_state.all_results = load_from_db() #values from DB are being loaded into sesion_state
        expected_keys = {(index_name, leverage) for index_name in index_map.keys() for leverage in [3, 5, 10]}
        missing_keys = expected_keys - set(st.session_state.all_results.keys())

        if missing_keys: #Data from DB is not complete/empty -> New Data needs to be calculated
            with st.spinner("Precomputing.. " + get_random_phrase()):
                new_results = precompute_all_simulations(keys_to_compute=missing_keys) #if db was empty: missing keys = all available keys
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
            new_results = precompute_all_simulations(keys_to_compute=missing_keys) 
            store_to_db(new_results)
            st.session_state.all_results.update(new_results)
            st.cache_data.clear()

    #st.session_state.refresh_data = False #Deactivating button to be cklickable again
    st.session_state.simulations_loaded = True

    # Force rerun
    st.rerun()


#If data is still not loaded: Error
if st.session_state.selected_index is None or st.session_state.all_results is None:
    st.error("Data not loaded properly. Selected index or results are missing.")
    st.stop()

#Storing calculations in current
current = st.session_state.all_results[(st.session_state.selected_index, st.session_state.selected_leverage)]


#assigning current values for all indices and leverage
df_all_index = current["df_all_index"]
df_investment = current["df_investment"]
df_plot_filtered = current["df_plot_filtered"]
remaining_budget = current["remaining_budget"]
cumulative_value = current["cumulative_value"]
metrics = current["metrics"]


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
    st.subheader(f"Index performance - {st.session_state.selected_index}")

    #Offset of Legend to be in top left corner
    legend = alt.Legend(
        orient="none",
        legendX=10,
        legendY=10
    )

    #Base chart
    base = alt.Chart(df_plot_filtered).encode(
        x=alt.X("date:T", title="Datum", axis=alt.Axis(format="%d %b %y"))
    )

    #Group for the indipendent left axis
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
    right_axis_group = alt.Chart(df_investment).transform_calculate(
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

    #Combining Charts to be displayed as one
    combined_chart = alt.layer(
        left_axis_group,
        right_axis_group
    ).resolve_scale(
        y="independent"
    )

    st.altair_chart(combined_chart, width="stretch")
    

#Metrics and settings
with mid:
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


    mid_left, mid_right = st.columns([0.7, 0.3])

    #Metrics of total investment
    with mid_left:

        with st.container(border=True):

            st.subheader("Current metrics")

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric("Investment-Level", f"€ {round(cumulative_value, 2):,.2f}".replace(",", " "))
                current_index_value = float(df_all_index["index_value"].iloc[-1])
                st.metric("Index-Level", f"{current_index_value:,.3f}".replace(",", " "))

            with col2:
                st.metric("Profit", f"€ {metrics['final_profit']:,.2f}".replace(",", " "))
                st.metric("Sells (Leverage < 1.5x)", f"{metrics['sells_count']}", f"{round( (metrics['sells_count'] / metrics['trades_count'] if not 0 else 1) * 100, 2 )} % of total", delta_arrow="off")

            with col3:
                st.metric("Losses", f"€ {metrics['loss_sum']:,.2f}".replace(",", " "))
                st.metric("KnockOuts", f"{metrics['knockouts_count']}", f"{round( (metrics['knockouts_count'] / metrics['trades_count'] if not 0 else 1) * 100, 2 )} % of total", delta_color="inverse", delta_arrow="off")

            with col4:
                st.metric("ROI", f"{metrics['total_return']} %", )
                st.metric("Active investments", f"{metrics['active_trades']}", f"{round( (metrics['active_trades'] / metrics['trades_count'] if not 0 else 1) * 100, 2 )} % of total" , delta_arrow="off")

            with col5:
                st.metric("Accessible budget", f"€ {remaining_budget:,.2f}".replace(",", " "))
                st.metric("Monthly budget", f"€ 500,00")
                #st.metric("Trades with not enough Budget to start", f"{metrics['not_enough_money_count']}")
                

    #Settings for Dashboard
    with mid_right:
        with st.container(border=True):

            st.subheader("Settings")

            col1, col2 = st.columns(2)

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
            
        with st.container(border=False):
            if st.button("Refresh Data"):
                #st.session_state.refresh_data = True
                data_refresh()

    st.markdown('</div>', unsafe_allow_html=True)


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
            df_display[["inv_id", "closing_reason"]],
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

            with col2:
                starting_investment = round(selected_row_data['starting_investment'], 2)
                st.metric("Start-Value", f"€ {starting_investment}")

            with col3:
                if selected_row_data['active']:
                    current_value = selected_row_data['current_value']
                    st.metric("Current Value", f"€ {current_value:,.2f}".replace(",", " "))

                elif not selected_row_data['active']:
                    closing_date = selected_row_data['closing_date']
                    st.metric("End", f" {closing_date}")

            with col4:
                st.metric("Status", closing_reason_text)

            with col5:
                profit_value = selected_row_data['profit']
                st.metric("Profit", f"€ {profit_value:,.2f}".replace(",", " "))

            with col6:
                indiv_return  = round( ((profit_value / starting_investment if starting_investment != 0 else 0)*100), 2)   
                st.metric("ROI", f"{indiv_return} %")
                
        else:
            st.info("Choose an investment from the table")



