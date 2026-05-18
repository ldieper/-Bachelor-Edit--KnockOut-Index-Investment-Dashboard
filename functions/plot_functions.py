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
    
    # Calculate absolute distance from index to barrier
    abs_dist = (df_plot["index_value"] - df_plot["knockout_barrier"]).abs()
    
    # Rank by distance within each date group, keep only top N (defaut = 2)
    rank = df_plot.groupby("date").cumcount()
    df_plot_temp = df_plot.assign(abs_dist=abs_dist, rank=rank)
    df_plot_temp["rank"] = df_plot_temp.groupby("date")["abs_dist"].rank(method="first")
    
    return df_plot_temp[df_plot_temp["rank"] <= top_n].drop(columns=["abs_dist", "rank"])