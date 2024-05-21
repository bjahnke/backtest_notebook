import pandas as pd
from src.regime.utils import (
    retest_from_latest_base_swing,
    find_all_retest_swing,
    add_peak_regime_data,
)

def get_stock_data(_symbol, _interval, _neon_db_url):
    q = (
        "select {table}.*, stock.symbol, stock.is_relative "
        "from {table} "
        "left join stock on {table}.stock_id = stock.id "
        "where stock.symbol = '{symbol}' "
        "and stock.interval = '{interval}' "
        "{extra}"
    ).format

    _stock_data = pd.read_sql \
        (q(table='stock_data', symbol=_symbol, interval=_interval, extra="order by stock_data.bar_number asc"), con=_neon_db_url)
    _regime_data = pd.read_sql(q(table='regime', symbol=_symbol, interval=_interval, extra=""), con=_neon_db_url)
    _peak_data = pd.read_sql(q(table='peak', symbol=_symbol, interval=_interval, extra=""), con=_neon_db_url)
    _fc_data = pd.read_sql(q(table='floor_ceiling', symbol=_symbol, interval=_interval, extra=""), con=_neon_db_url)
    return _stock_data, _regime_data, _peak_data, _fc_data


def get_data_by_market(_market_index, _interval, _neon_db_url, tables=None):
    if tables is None:
        tables = ['stock_data', 'regime', 'peak']
    q = (
         "select {table}.*, stock.symbol, stock.is_relative "
         "from {table} "
         "left join stock on {table}.stock_id = stock.id "
         "where stock.market_index = '{market}' "
         "and stock.interval = '{interval}' "
         "{extra}"
    ).format
    table_lookup = {
        'stock_data': lambda: pd.read_sql(q(table='stock_data', market=_market_index, interval=_interval, extra="order by stock_data.bar_number asc"), con=_neon_db_url),
        'regime': lambda: pd.read_sql(q(table='regime', market=_market_index, interval=_interval, extra=""), con=_neon_db_url),
        'peak': lambda: pd.read_sql(q(table='peak', market=_market_index, interval=_interval, extra=""), con=_neon_db_url)
    }
    result = [table_lookup[table]() for table in tables]
    return result

import src.regime.utils
def plot(_stock_data, title, entries=False, secondary_y=None, style_map=None):
    if secondary_y is None:
        secondary_y = ['fc', 'sma', 'bo', 'tt']
    sd = _stock_data.copy()

    style_map = {
        'close': '-', # line

        'lo3': 'g^', # green up arrow
        'dlo3': 'k^', # black up arrow (white for dark mode)

        'hi3': 'rv', # red down arrow
        'dhi3': 'kv', # black down arrow (white for dark mode)

        'lo2': 'g.', # green dot
        'dlo2': 'k.', # black dot (white for dark mode)

        'hi2': 'r.', # red dot
        'dhi2': 'm.', # magenta dot

        'fc': 'b--', # blue dashed line
        'sma': 'y--', # yellow dashed line
        'bo': 'k--', # black dashed line (white for dark mode)
        'tt': 'c--', # cyan dashed line
        # make fc_val green
        'fc_val': 'y*',
        # make rg_ch_val yellow start
        'rg_ch_val': 'c--',
        'trading_range_lo_band': 'r--',
        'trading_range_hi_band': 'g--',
    }
    if entries:
        if sd.fc.iloc[-1] == 1:
            del style_map['hi2']
            del style_map['dhi2']
            del style_map['hi3']
            del style_map['dhi3']
        else:
            del style_map['lo2']
            del style_map['dlo2']
            del style_map['lo3']
            del style_map['dlo3']

    remove_keys = []
    for key, val in style_map.items():
        if key not in sd.columns:
            remove_keys.append(key)
    for key in remove_keys:
        style_map.pop(key)

    try:
        sd[
            style_map.keys()].plot(style=list(style_map.values()), secondary_y=secondary_y, figsize=(15, 10), title=title)
    except KeyError:
        pass

def setup_trend_view_graph(stock_data, regime_data, peak_data, fc_data):
    peak_data.lvl = peak_data.lvl.astype(int)
    stock_data.index = stock_data.bar_number
    stock_data.index.name = 'index'
    relative_stock_data = add_peak_regime_data(
        stock_data.loc[stock_data.is_relative == True],
        regime_data.loc[regime_data.is_relative == True],
        peak_data.loc[peak_data.is_relative == True]
    )
    relative_stock_data = add_fc_data(relative_stock_data, fc_data.loc[fc_data.is_relative == True])
    absolute_stock_data = add_peak_regime_data(
        stock_data.loc[stock_data.is_relative == False],
        regime_data.loc[regime_data.is_relative == False],
        peak_data.loc[peak_data.is_relative == False]
    )
    absolute_stock_data = add_fc_data(absolute_stock_data, fc_data.loc[fc_data.is_relative == False])
    return absolute_stock_data, relative_stock_data


def setup_trend_view_graph_simple(stock_data, regime_data, peak_data, fc_data):
    _stock_data = add_peak_regime_data(stock_data, regime_data, peak_data)
    _stock_data = add_fc_data(_stock_data, fc_data)
    return _stock_data


def add_regime_data(_price_data, _regime_data):
    for index, row in _regime_data.iterrows():
        _price_data.loc[row.start:row.end, row.type] = row.rg
    return _price_data


def add_fc_data(_stock_data, _fc_data):
    fc_val_table = _fc_data[['fc_val', 'fc_date']]
    # drop duplicate fc_dates
    fc_val_table = fc_val_table.drop_duplicates(subset=['fc_date'])
    _stock_data = _stock_data.reset_index().rename(columns={'index': 'bar_number'})
    _stock_data = _stock_data.merge(
        fc_val_table, how='left', left_on='bar_number', right_on='fc_date')

    rg_change_table = _fc_data[['rg_ch_val', 'rg_ch_date']]
    _stock_data = _stock_data.merge(
        rg_change_table, how='left', left_on='bar_number', right_on='rg_ch_date')
    _stock_data.rg_ch_val = _stock_data.rg_ch_val.ffill()
    return _stock_data