import pandas as pd


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
    return _stock_data, _regime_data, _peak_data


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


def plot(_stock_data, title):
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
        'tt': 'c--' # cyan dashed line
    }
    remove_keys = []
    for key, val in style_map.items():
        if key not in _stock_data.columns:
            remove_keys.append(key)
    for key in remove_keys:
        style_map.pop(key)
    secondary_y = ['fc', 'sma', 'bo', 'tt']
    try:
        _stock_data[
            style_map.keys()].plot(style=list(style_map.values()), secondary_y=secondary_y, figsize=(15, 10), title=title)
    except KeyError:
        pass