import pathlib

import pandas as pd
from data_manager import scanner
from data_manager.utils import simple_relative
from sqlalchemy import create_engine
import scripts.env as env
import mytypes
from typing import Type
import schedule
import time

def _download_data(stock_table_url: str = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies',
                    bench: str = 'SPY',
                    days: int = 365,
                    interval_str: str = '1d') -> tuple:
    """
    Download stock price data and benchmark data.

    :param stock_table_url: URL of the stock table on Wikipedia.
    :param bench: The symbol of the benchmark to use.
    :param days: Number of days of historical data to download.
    :param interval_str: The interval of the historical data to download.
    :return: A tuple containing the downloaded stock data and benchmark data.
    """
    ticks, _ = scanner.get_wikipedia_stocks(stock_table_url)
    downloaded_data = scanner.yf_download_data(ticks, days, interval_str)
    bench_data = scanner.yf_get_stock_data(bench, days, interval_str)
    bench_data['symbol'] = bench
    return downloaded_data, bench_data

def _build_tables(downloaded_data: pd.DataFrame,
                   bench_data: pd.DataFrame,
                   interval_str: str) -> tuple:
    """
    Build the historical and timestamp tables.

    :param downloaded_data: The downloaded stock price data.
    :param bench_data: The benchmark data.
    :param interval_str: The interval of the historical data.
    :return: A tuple containing the historical data and timestamp data.
    """
    downloaded_data = downloaded_data.reset_index()
    dd_timestamp = downloaded_data.columns.to_list()[0]
    dd_date_time = downloaded_data[dd_timestamp]
    bench_data = bench_data.reset_index()
    bd_date_time = bench_data[bench_data.columns.to_list()[0]]
    #remove timestamp column
    downloaded_data = downloaded_data.iloc[:, 1:]
    bench_data = bench_data.iloc[:, 1:]

    # ensure bench has same dates as stock data
    assert dd_date_time.equals(bd_date_time)

    # melt multiindex df (stretch vertically)
    relative = simple_relative(downloaded_data, bench_data.close)
    downloaded_data = downloaded_data.reset_index().rename(columns={'index': 'bar_number'})
    relative = relative.reset_index().rename(columns={'index': 'bar_number'})
    relative = modify_dataframe(relative)

    # create timestamp table
    timestamp_data = downloaded_data[['bar_number']].copy()
    timestamp_data['interval'] = interval_str
    timestamp_data['timestamp'] = dd_date_time
    timestamp_data.columns = timestamp_data.columns.droplevel(1)

    downloaded_data = modify_dataframe(downloaded_data)

    # create historical table
    relative['is_relative'] = True
    downloaded_data['is_relative'] = False
    bench_data['is_relative'] = False

    historical_data = pd.concat([downloaded_data, relative, bench_data], axis=0)
    historical_data['interval'] = interval_str

    return historical_data, timestamp_data

def modify_dataframe(data: pd.DataFrame) -> pd.DataFrame:
    """
    Modify the input dataframe to make it suitable for the database.

    :param data: The dataframe to modify.
    :return: The modified dataframe.
    """
    # Melt dataframe to stack the columns
    data = data.melt(id_vars='bar_number', var_name=['type', 'symbol'], value_name='value')
    # Pivot the 'type' column to expand the dataframe vertically
    data = data.pivot_table(index=['symbol', 'bar_number'], columns='type', values='value').reset_index()
    return data


def save_historical_data_to_database(stock_data: pd.DataFrame,
                                     bench_data: pd.DataFrame,
                                     engine,
                                     hp: Type[env.HistoricalPrices],
                                     download_params: mytypes.DownloadParams) -> None:
    """
    Save historical stock price data to a database.

    :param stock_data: The downloaded stock price data.
    :param bench_data: The benchmark data.
    :param engine: A `ConnectionSettings` object containing the database connection settings.
    :param hp: A `HistoricalPrices` class object containing the name of the table to save the data to.
    :param download_params: Download parameters.
    """
    # tables = _download_data(**download_params.dict())
    historical_data, timestamp_data = _build_tables(stock_data, bench_data, interval_str=download_params.interval_str)

    historical_data['interval'] = download_params.interval_str
    historical_data.to_sql(hp.stock_data, engine, index=False, if_exists='replace')
    timestamp_data.to_sql(hp.timestamp_data, engine, index=False, if_exists='replace')


def task_save_historical_data_to_database() -> None:
    """
    Schedule the script to save historical data to a database.
    """
    engine = create_engine(URL.create(
        **env.get_connection_settings(env.HISTORICAL_PRICES_DB).dict()
    ))
    save_historical_data_to_database(
        engine,
        env.HistoricalPrices,
        mytypes.DownloadParams()
    )

def init_schedule(trigger_time: str = "02:30") -> None:
    """
    Schedule the script to run once a day at a specific time.

    :param trigger_time: The time to run the script.
    """
    # Schedule the script to run once a day at 2:30am
    schedule.every().day.at(trigger_time).do(task_save_historical_data_to_database)

    while True:
        # Check if any scheduled jobs are due to run
        schedule.run_pending()
        time.sleep(1)


def re_download_stock_data() -> None:
    """
    Download and cache stock data locally for testing.
    """
    stock_data, bench_data = _download_data(**mytypes.DownloadParams().dict())
    stock_data.to_pickle(pathlib.Path('..') / 'data' / 'stock_data_raw_push_test.pkl')
    bench_data.to_pickle(pathlib.Path('..') / 'data' / 'bench_data_raw_push_test.pkl')


def load_pickle_stock_data() -> tuple:
    """
    Load price data from pickle for testing.

    :return: A tuple containing the stock data and benchmark data.
    """
    stock_data = pd.read_pickle(pathlib.Path('..') / 'data' / 'stock_data_raw_push_test.pkl')
    bench_data = pd.read_pickle(pathlib.Path('..') / 'data' / 'bench_data_raw_push_test.pkl')
    return stock_data, bench_data


if __name__ == '__main__':
    _stock_data, _bench_data = _download_data(**mytypes.DownloadParams().dict())
    save_historical_data_to_database(
        _stock_data,
        _bench_data,
        env.ConnectionEngines.HistoricalPrices.NEON,
        env.HistoricalPrices,
        download_params=mytypes.DownloadParams()
    )





