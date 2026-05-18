from datetime import datetime, timedelta

#Gets the last trading day
def get_last_trading_day():
    today = datetime.today()
    weekday = today.weekday()  #Monday = 0, Sunday = 6

    if weekday == 0:  #Monday till Friday
        delta = 3
    elif weekday == 6:  #Sunday till Friday
        delta = 2
    else:
        delta = 1

    return today - timedelta(days=delta)

#Gets last day of the dataframes investments
def get_last_investment_day(source):
    return source["date"].max()