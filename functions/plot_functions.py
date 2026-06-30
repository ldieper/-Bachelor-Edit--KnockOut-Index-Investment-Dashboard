import pandas as pd
import altair as alt

#Function to create a plot for a individualk investment
def create_investment_detail_plot(df_investment, df_all_index, inv_id):
    if inv_id is None:
        return None
    
    # Filter to only this investment
    df_inv = df_investment[df_investment["inv_id"] == inv_id][["date", "current_value", "leverage", "knockout_barrier"]].copy()
    
    if df_inv.empty:
        return None
    
    # Merge with index data for comparison
    df_plot_detail = pd.merge(
        df_all_index[["date", "index_value"]],
        df_inv,
        on="date",
        how="inner"
    )

    legend = alt.Legend(
    orient="top"
    )

    color = alt.Color(
        "lines:N",
        legend=legend,
        scale=alt.Scale(
            domain=["Index", "Barrier", "Investment"],
            range=["#BA2BAC", "#c4265e", "#e2e22e"]
        )
    )
    
    #Create base chart with X axis
    base = alt.Chart(df_plot_detail).encode(
        x=alt.X("date:T", title="Datum", axis=alt.Axis(format="%d %b %y"))
    )
    
    #Index value and Knockout barrier
    line_index = base.transform_calculate(
        lines="'Index'"
        ).mark_line(size=2).encode(
            y=alt.Y("index_value:Q", title="Index & Barrier Value", scale=alt.Scale(zero=False)),
            color=color
    )
    
    line_barrier = base.transform_calculate(
        lines="'Barrier'"
        ).mark_line(strokeDash=[5, 5], size=2).encode(   
            y=alt.Y("knockout_barrier:Q", scale=alt.Scale(zero=False)),
            color=color
    )
    
    #Investment value (independent scale)
    line_investment = base.transform_calculate(
        lines="'Investment'"
        ).mark_line(size=2.5).encode(
            y=alt.Y("current_value:Q", title="Investment Value (€)", scale=alt.Scale(zero=False), axis=alt.Axis(orient="right")),
            color=color
    )
    

    left_chart = alt.layer(line_index, line_barrier)
    
    chart = alt.layer(left_chart, line_investment).resolve_scale(
        y="independent"
    ).properties(
        height=250,
        title=f"Investment: {int(inv_id)}",
    )
    
    return chart


#Function to only display the top n barriers for readability
def filter_nearest_barriers(df_plot, top_n=1):
    if "knockout_barrier" not in df_plot.columns or df_plot["knockout_barrier"].isna().all():
        return df_plot
    
    # Keep all rows first
    df_result = df_plot.copy()
    
    # Only filter barriers, not index values
    df_with_barriers = df_plot[df_plot["knockout_barrier"].notna()].copy()
    
    if df_with_barriers.empty:
        return df_result
    
    # Calculate absolute distance from index to barrier
    abs_dist = (df_with_barriers["index_value"] - df_with_barriers["knockout_barrier"]).abs()
    
    # Rank by distance within each date group, keep only top N (default = 1)
    df_with_barriers_temp = df_with_barriers.assign(abs_dist=abs_dist)
    df_with_barriers_temp["rank"] = df_with_barriers_temp.groupby("date")["abs_dist"].rank(method="first")
    
    # Keep only top N barriers per date
    df_barriers_filtered = df_with_barriers_temp[df_with_barriers_temp["rank"] <= top_n].drop(columns=["abs_dist", "rank"])
    
    # Set barriers to NaN for rows not in the filtered set
    df_result.loc[~df_result.index.isin(df_barriers_filtered.index), "knockout_barrier"] = None
    df_result.loc[df_barriers_filtered.index, "knockout_barrier"] = df_barriers_filtered["knockout_barrier"]
    
    return df_result