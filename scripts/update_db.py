import pandas as pd
from data_manager import scanner
from data_manager.utils import simple_relative
from sqlalchemy import URL, create_engine
import scripts.env as env
import mytypes
from typing import Type


def _download_data(
        stock_table_url: str = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies',
        bench: str = 'SPY',
        days: int = 365,
        interval_str: str = '1d'
):
    ticks, _ = scanner.get_wikipedia_stocks(stock_table_url)
    downloaded_data = scanner.yf_download_data(ticks, days, interval_str)
    bench_data = scanner.yf_get_stock_data(bench, days, interval_str)
    bench_data['symbol'] = bench
    return downloaded_data, bench_data

def _build_tables(downloaded_data: pd.DataFrame, bench_data: pd.DataFrame):
    downloaded_data = downloaded_data.reset_index()
    dd_date_time = downloaded_data[downloaded_data.columns.to_list()[0]]
    bench_data = bench_data.reset_index()
    bd_date_time = bench_data[bench_data.columns.to_list()[0]]

    assert dd_date_time.equals(bd_date_time)

    downloaded_data = downloaded_data[downloaded_data.columns.to_list()[1:]]
    bench_data = bench_data[bench_data.columns.to_list()[1:]]
    relative = simple_relative(downloaded_data, bench_data.close)
    return downloaded_data, bench_data, dd_date_time, relative

def modify_dataframe(data):
    # Download the data

    # Reset index and add bar_number column
    data = data.reset_index().rename(columns={'index': 'bar_number'})

    # Melt dataframe to stack the columns
    data = data.melt(id_vars='bar_number', var_name=['type', 'symbol'], value_name='value')

    # Pivot the 'type' column to expand the dataframe vertically
    data = data.pivot_table(index=['symbol', 'bar_number'], columns='type', values='value').reset_index()

    return data


def save_historical_data_to_database(db_connect_settings: mytypes.ConnectionSettings, hp: Type[env.HistoricalPrices]):
    """
    Save historical stock price data to a database.

    :param db_connect_settings: A `ConnectionSettings` object containing the database connection settings.
    :param hp: A `HistoricalPrices` class object containing the name of the table to save the data to.
    """
    tables = _download_data()
    downloaded_data, bench_data, dd_date_time, relative = _build_tables(*tables)

    relative = modify_dataframe(relative)
    downloaded_data = modify_dataframe(downloaded_data)

    relative['is_relative'] = True
    downloaded_data['is_relative'] = False
    bench_data['is_relative'] = False

    historical_data = pd.concat([downloaded_data, relative, bench_data], axis=0)
    engine = create_engine(URL.create(
        **db_connect_settings.dict()
    ))
    historical_data.to_sql(hp.stock_data, engine, index=False, if_exists='replace')
    dd_date_time.to_sql(hp.stock_data, engine, index=False, if_exists='replace')


def task_save_historical_data_to_database():
    save_historical_data_to_database(
        env.get_connection_settings(env.HISTORICAL_PRICES_DB),
        env.HistoricalPrices
    )


if __name__ == '__main__':

    import schedule
    import time


    # Schedule the script to run once a day at 2:30am
    schedule.every().day.at("02:30").do(task_save_historical_data_to_database)

    while True:
        # Check if any scheduled jobs are due to run
        schedule.run_pending()
        time.sleep(1)

