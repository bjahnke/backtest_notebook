from backtesting import Backtest, Strategy
from backtesting.lib import crossover

from backtesting.test import SMA, GOOG
from coinbase.rest import RESTClient as cbRestClient
from datetime import datetime, timedelta
import time

# class SmaCross(Strategy):
#     def init(self):
#         price = self.data.Close
#         self.ma1 = self.I(SMA, price, 10)
#         self.ma2 = self.I(SMA, price, 20)

#     def next(self):
#         if crossover(self.ma1, self.ma2):
#             self.buy()
#         elif crossover(self.ma2, self.ma1):
#             self.sell()


# bt = Backtest(GOOG, SmaCross, commission=.002,
#               exclusive_orders=True)
# stats = bt.run()
# bt.plot()


import pandas as pd
import numpy as np

# Initialize the client with your API key and secret
client = cbRestClient(key_file='C:\cdp_api_key.json')

def cme_gap_backtest(price_data: pd.DataFrame, initial_balance: float, initial_crypto: float, weekly_allowance: float = 1500):
    """
    Backtests the CME gap strategy based on hourly price data.
    
    :param price_data: DataFrame containing the hourly crypto price data. It must contain a 'timestamp' column and a 'price' column.
    :param initial_balance: Initial cash balance (in USD).
    :param initial_crypto: Initial amount of cryptocurrency (in BTC or any other crypto).
    :param weekly_allowance: Amount to withdraw as a weekly allowance (default: $1500).
    :return: A DataFrame with the backtest results.
    """
    # Convert timestamps to datetime
    price_data['timestamp'] = pd.to_datetime(price_data['timestamp'])
    price_data.set_index('timestamp', inplace=True)
    
    # Track portfolio
    balance = initial_balance
    crypto = initial_crypto
    net_worth = []
    week_starts = price_data.resample('W-MON').first().index
    trade_history = []
    
    for i in range(len(week_starts) - 1):
        # Get data for the current week
        week_data = price_data.loc[week_starts[i]:week_starts[i+1]]
        
        # Get Friday 4 PM Central closing price
        friday_close = week_data.between_time('22:00', '22:00', include_end=False).last('1D')  # Adjust timezone as needed
        if friday_close.empty:
            continue
        friday_close_price = friday_close['price'].iloc[-1]
        
        # Place sell orders at 1.5%, 3%, 5%, etc. above the Friday close price
        sell_prices = friday_close_price * (1 + np.array([0.015, 0.03, 0.05, 0.075, 0.10, 0.125, 0.15, 0.20]))
        
        # Loop over the weekend and check if the sell orders are hit
        for sell_price in sell_prices:
            sell_data = week_data[week_data['price'] >= sell_price]
            if not sell_data.empty:
                # Execute the sell order
                amount_sold = crypto * 0.015  # Sell 1.5% at each level
                balance += amount_sold * sell_price
                crypto -= amount_sold
                trade_history.append({'timestamp': sell_data.index[0], 'action': 'sell', 'price': sell_price, 'amount': amount_sold})
        
        # Clear remaining sell orders on Sunday 3 PM Central and keep buys open
        sunday_reopen = week_data.between_time('21:00', '21:00', include_end=False).first('1D')
        if not sunday_reopen.empty:
            sunday_price = sunday_reopen['price'].iloc[0]
            buy_back = week_data[week_data['price'] <= friday_close_price]
            if not buy_back.empty:
                amount_bought = crypto * 0.015  # Buy back amount sold at 1.5%
                balance -= amount_bought * friday_close_price
                crypto += amount_bought
                trade_history.append({'timestamp': buy_back.index[0], 'action': 'buy', 'price': friday_close_price, 'amount': amount_bought})
        
        # Withdraw weekly allowance
        if balance >= weekly_allowance:
            balance -= weekly_allowance
        
        # Track net worth for the week
        net_worth.append({
            'week': week_starts[i],
            'balance': balance,
            'crypto': crypto,
            'total_value': balance + (crypto * friday_close_price)
        })
    
    # Convert net worth to DataFrame for analysis
    net_worth_df = pd.DataFrame(net_worth).set_index('week')
    return net_worth_df, pd.DataFrame(trade_history)

# Example usage
# price_data = pd.read_csv('crypto_price_data.csv')  # Load your hourly price data here
# result, trade_history = cme_gap_backtest(price_data, initial_balance=50000, initial_crypto=5)

# Now, 'result' will contain the week-by-week portfolio performance, and 'trade_history' will contain all trades executed.

def coinbase_granularity_to_datetime(granularity: str, bar_count: int):
    """translate coinbase ENUM granularity to a datetime timedelta"""
    if granularity == 'ONE_MINUTE':
        return timedelta(minutes=bar_count)
    elif granularity == 'FIVE_MINUTE':
        return timedelta(minutes=5*bar_count)
    elif granularity == 'FIFTEEN_MINUTE':
        return timedelta(minutes=15*bar_count)
    elif granularity == 'ONE_HOUR':
        return timedelta(hours=bar_count)
    elif granularity == 'SIX_HOUR':
        return timedelta(hours=6*bar_count)
    elif granularity == 'ONE_DAY':
        return timedelta(days=1*bar_count)
    else:
        raise ValueError('Granularity not supported')

def get_price_history(product_id: str, bars: int, granularity: str, end_date=None):
    all_data = []
    remaining_bars = bars
    current_end_date = end_date

    

    while remaining_bars > 0:
        fetch_bars = min(remaining_bars, 300)
        data = _get_price_history(product_id, fetch_bars, granularity, current_end_date)
        all_data.append(data)
        remaining_bars -= fetch_bars
        current_end_date = data['start'].min() - coinbase_granularity_to_datetime(granularity, fetch_bars)

    res = pd.concat(all_data).sort_values(by='start').reset_index(drop=True)
    res = res.astype({
        'low': 'float',
        'high': 'float',
        'open': 'float',
        'close': 'float',
        'volume': 'float',
    })

    return res


def _get_price_history(product_id: str, bars: int, granularity: str, end_date=None):
    """
    Fetches historical price data (OHLC candles) from Coinbase for a given product.
    
    :param product_id: The trading pair (e.g., 'BTC-USD').
    :param start_date: Start date for the price history (datetime object, only date part is used).
    :param end_date: End date for the price history (datetime object, only date part is used).
    :param granularity: The time period for each candle (in seconds), e.g., 3600 for 1-hour candles.
    :return: A list of OHLC data (time, low, high, open, close, volume).
    """
    if end_date is None:
        end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - coinbase_granularity_to_datetime(granularity, bars)

    # Format start and end dates to ISO 8601 strings (YYYY-MM-DD format)
    start_date = int(start_date.timestamp())
    end_date = int(end_date.timestamp())
    # Fetch candles with ISO 8601 date strings
    candles = client.get_candles(
        product_id=product_id,
        start=start_date,
        end=end_date,
        granularity=granularity
    )
    price_data = pd.DataFrame(candles['candles'])
    price_data = price_data.iloc[::-1].reset_index(drop=True)
    price_data['start'] = pd.to_datetime(price_data['start'], unit='s')
    return price_data


def get_gap_fill_row(price_data, friday_close, monday_open_date):
    """
    Query prices from Monday onward where low is ≤ friday close.
    If not empty, return the first occurrence, else return None.
    
    :param price_data: DataFrame containing OHLC data with a datetime index.
    :param friday_close: The close price of the previous Friday.
    :param monday_open_date: The date of the Monday open.
    :return: The first occurrence where low is ≤ friday close, else None.
    """
    monday_onward = price_data[price_data.index >= monday_open_date]
    gap_fill = monday_onward[monday_onward['low'] <= friday_close]
    if not gap_fill.empty:
        return gap_fill.iloc[0]
    return None


def create_friday_monday_table(price_data: pd.DataFrame):
    """
    Create a table that includes each Friday date and the following Monday date.

    :param price_data: DataFrame containing OHLC data with a datetime index and a 'day_of_week' column.
    :return: DataFrame with columns 'Friday' and 'Monday' containing the respective dates.
    """
    # Ensure the data is sorted by date
    price_data = price_data.sort_index()

    # Filter Fridays and Mondays
    fridays = price_data[price_data['day_of_week'] == 4]
    mondays = price_data[price_data['day_of_week'] == 0]

    # Create a list to store the pairs
    friday_monday_pairs = []

    for friday_date in fridays.index:
        # Find the following Monday
        next_monday = mondays[mondays.index > friday_date].index.min()
        if pd.notna(next_monday):
            friday_monday_pairs.append((friday_date, next_monday))

    # Create a DataFrame from the pairs
    friday_monday_table = pd.DataFrame(friday_monday_pairs, columns=['friday', 'monday'])

    return friday_monday_table


def build_weekend_gap_tables(price_data: pd.DataFrame):
    """
    Note: currently only checks gap ups

    Analyze gaps in the price data and calculate the percentage of gaps that get filled.
    
    :param price_data: DataFrame containing OHLC data with a datetime index.
    :return: The percentage of gaps that get filled.
    """
    price_data['day_of_week'] = price_data.start.dt.dayofweek
    gap_table = create_friday_monday_table(price_data)

    gap_records = []
    gap_fill_records = []

    for _, row in gap_table.iterrows():
        friday_data = price_data.loc[row['friday']]
        monday_data = price_data.loc[row['monday']]

        if monday_data['open'] > friday_data['close']:
            params = {
                'direction': 'up',
                'query': lambda x: x['low'] <= friday_data['close']
            }
        elif monday_data['open'] < friday_data['close']:
            params = {
                'direction': 'down',
                'query': lambda x: x['high'] >= friday_data['close']
            }
        else:
            continue

        gap_records.append((row['friday'], row['monday'], params['direction']))
        data_after_gap = price_data.loc[row['monday']:]
        gap_fill_index = data_after_gap.loc[params['query'](data_after_gap)].first_valid_index()
        if gap_fill_index is not None:
            gap_fill_records.append((len(gap_records)-1, gap_fill_index))
    
    gap_fill_table = pd.DataFrame(gap_fill_records, columns=['gap_id', 'gap_fill_date'])
    gap_table = pd.DataFrame(gap_records, columns=['gap_start_date', 'gap_end_date', 'gap_type'])
    return gap_table, gap_fill_table


def gap_fill_test_main(symbol):
    # Load your daily price data here
    products = client.get_products()
    pdf = pd.DataFrame(products['products'])
    price_data = get_price_history('BTC-USD', bars=300, granularity='ONE_DAY')

    
    gap_fill_percentage, gap_table, gap_fill_table = build_weekend_gap_tables(price_data)
    print(f"Percentage of gaps that get filled: {gap_fill_percentage * 100:.2f}%")
    print("Gap Table:", gap_table)
    print("Gap Fill Table:", gap_fill_table)

# Example usage
def history_main():
    client.get_accounts()
    # Define the product (trading pair)
    product = 'BTC-USD'
    
    # Define the date range (last 3 days)
    end_date = time.time()
    
    # Set the granularity (86400 seconds = 1-day candles)
    granularity = 'ONE_HOUR'  # 1-day candles
    seconds_in_a_day = 24 * 60 * 60
    days_ago = 5
    start_date = end_date - (days_ago * seconds_in_a_day)
    # Fetch the price history
    start_date = end_date - timedelta(days=5)

    candles = get_price_history(product, start_date, granularity)
    candles = pd.DataFrame(candles['candles'])
    print(candles)

if __name__ == "__main__":
    gap_fill_test_main()