import dotenv
import src.regime.utils
import matplotlib.pyplot as plt
import pandas as pd
from typing import Any, Dict, TypedDict
from typing import Generic, TypeVar
from src.regime.utils import (
    retest_from_latest_base_swing,
    find_all_retest_swing,
    add_peak_regime_data,
)

dotenv.load_dotenv()

class Market:
    @staticmethod
    def market_analysis_macro(source_connection: str):
        return Market.market_trend_analysis(*Market.load_tables(source_connection))

    @staticmethod
    def load_tables(source_connection: str):
        regime_table = pd.read_sql(f'SELECT * FROM regime', source_connection)
        stock_table = pd.read_sql("SELECT id, symbol, is_relative FROM stock where stock.data_source = 'yahoo' and stock.market_index = 'SPY'", source_connection)
        web_df = pd.read_sql("SELECT * FROM stock_info", source_connection)
        return regime_table, stock_table, web_df

    @staticmethod
    def market_trend_analysis(regime_table, stock_table, web_df):
        regime_cols = ['fc', 'fc_r', 'bo', 'bo_r', 'sma', 'sma_r', 'tt', 'tt_r']
        
        regime_table = stock_table.merge(regime_table, left_on='id', right_on='stock_id', how='inner')
        max_end_indices = regime_table.groupby(['symbol', 'type', 'is_relative'])['end'].idxmax()

        filtered_df = regime_table.loc[max_end_indices, ['symbol', 'type', 'is_relative', 'end', 'rg']].reset_index(drop=True)
        filtered_df['type'] = filtered_df['type'] + filtered_df['is_relative'].replace({True: '_r', False: ''})

        regime_overview = filtered_df.pivot(index=['symbol'], columns='type', values='rg').reset_index()
        regime_overview = regime_overview[['symbol'] + regime_cols]
        regime_overview['delta'] = 0
        regime_pairs = [('bo', 'bo_r'), ('fc', 'fc_r'), ('sma', 'sma_r'), ('tt', 'tt_r')]
        
        # if na, use the other value as default, else use 0 to avoid NaN calculations
        for absolute, relative in regime_pairs:
            regime_overview[absolute] = regime_overview[absolute].fillna(regime_overview[relative])
            regime_overview[relative] = regime_overview[relative].fillna(regime_overview[absolute])
            regime_overview[absolute] = regime_overview[absolute].fillna(0)
            regime_overview[relative] = regime_overview[relative].fillna(0)
            regime_overview['delta'] += (regime_overview[relative] - regime_overview[absolute])

        regime_overview['delta'] /= 2

        regime_overview['delta'] /= len(regime_pairs)
        regime_overview['score'] = regime_overview[regime_cols].sum(axis=1)
        full_regime_overview = regime_overview.merge(web_df[['symbol', 'GICS Sector', 'GICS Sub-Industry']], left_on='symbol', right_on='symbol')
        regime_overview = full_regime_overview.drop(columns=['symbol'])

        groupby_cols = ['score', 'delta'] + regime_cols
        sort_key = ['GICS Sector']
        sector_overview = regime_overview.groupby(sort_key)[groupby_cols].mean().sort_values(by='score')

        groupby_cols = ['score', 'delta'] + regime_cols
        sort_key = ['GICS Sub-Industry']
        sub_industry_overview = regime_overview.groupby(sort_key)[groupby_cols].mean().sort_values(
            by= 'score')
        
        groupby_cols = ['score', 'delta'] + regime_cols
        sort_key = ['GICS Sector','GICS Sub-Industry']

        sector_sub_sector_overview = regime_overview.groupby(sort_key)[groupby_cols].mean().sort_values(
            by= ['GICS Sector','score'])
        
        full_regime_overview = full_regime_overview[['symbol', 'delta', 'score', 'GICS Sector', 'GICS Sub-Industry']]
        
        return (
            ('Sector Overview', sector_overview), 
            ('Sub Industry Overview', sub_industry_overview), 
            ('Sub Sector/Sector Overview', sector_sub_sector_overview), 
            ('Full Market Overview', full_regime_overview),
        )

def get_stock_data(symbol, interval, data_source, _neon_db_url):
    q = (
        "select {table}.*, stock.symbol, stock.is_relative "
        "from {table} "
        "left join stock on {table}.stock_id = stock.id "
        f"where stock.symbol = '{symbol}' "
        f"and stock.interval = '{interval}' "
        f"and stock.data_source = '{data_source}'"
        "{extra}"
    ).format

    _stock_data = pd.read_sql(q(table='stock_data', extra="order by stock_data.bar_number asc"), con=_neon_db_url)
    _regime_data = pd.read_sql(q(table='regime', extra=""), con=_neon_db_url)
    _peak_data = pd.read_sql(q(table='peak', extra=""), con=_neon_db_url)
    _fc_data = pd.read_sql(q(table='floor_ceiling', extra=""), con=_neon_db_url)
    return _stock_data, _regime_data, _peak_data, _fc_data


def get_data_by_market(market_index, interval, _neon_db_url, tables=None):
    if tables is None:
        tables = ['stock_data', 'regime', 'peak']
    q = """--sql
        select {table}.*, stock.symbol, stock.is_relative
        from {table}
        left join stock on {table}.stock_id = stock.id
        where stock.market_index = '{market_index}'
        and stock.interval = '{interval}'
        {extra}
    """.format(market=market_index, interval=interval, table='{table}', extra='{extra}').format

    table_lookup = {
        'stock_data': lambda: pd.read_sql(q(table='stock_data', extra="order by stock_data.bar_number asc"), con=_neon_db_url),
        'regime': lambda: pd.read_sql(q(table='regime', extra=""), con=_neon_db_url),
        'peak': lambda: pd.read_sql(q(table='peak', extra=""), con=_neon_db_url)
    }
    result = [table_lookup[table]() for table in tables]
    return result


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
    relative_stock_data = setup_trend_view_helper(stock_data, regime_data, peak_data, fc_data, True)
    absolute_stock_data = setup_trend_view_helper(stock_data, regime_data, peak_data, fc_data, False)
    return absolute_stock_data, relative_stock_data


def setup_trend_view_helper(stock_data, regime_data, peak_data, fc_data, is_relative):
    stock_data = add_peak_regime_data(
        stock_data.loc[stock_data.is_relative == is_relative],
        regime_data.loc[regime_data.is_relative == is_relative],
        peak_data.loc[peak_data.is_relative == is_relative]
    )
    stock_data = add_fc_data(stock_data, fc_data.loc[fc_data.is_relative == is_relative])
    stock_data['rolling_max'] = stock_data.close.rolling(window=252).max()
    stock_data['rolling_min'] = stock_data.close.rolling(window=252).min()
    stock_data['trading_range'] = (stock_data.rolling_max - stock_data.rolling_min)
    stock_data['trading_range_lo_band'] = stock_data.rolling_min + stock_data.trading_range * .61
    stock_data['trading_range_hi_band'] = stock_data.rolling_min + stock_data.trading_range * .40
    return stock_data


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
    if 'bar_number' not in _stock_data.columns:
        _stock_data = _stock_data.reset_index().rename(columns={'index': 'bar_number'})
    _stock_data = _stock_data.merge(
        fc_val_table, how='left', left_on='bar_number', right_on='fc_date')

    rg_change_table = _fc_data[['rg_ch_val', 'rg_ch_date']]
    _stock_data = _stock_data.merge(
        rg_change_table, how='left', left_on='bar_number', right_on='rg_ch_date')
    _stock_data.rg_ch_val = _stock_data.rg_ch_val.ffill()
    return _stock_data


def plot_sector_on_bench(canvas, bench_df, rel, abs, selected: str):
    """
    Plot the sector data on the same plot as the benchmark data.
    Integrate with display library of choice.
    """
    # Create a figure and axes
    ax1 = canvas.axes

    # Plot the 'spy' data on the primary axis
    ax1.plot(bench_df.index, bench_df['close'], color='lightblue', label='SPY')

    # Set the y-axis label for the primary axis
    ax1.set_ylabel('SPY Price', color='lightblue')
    ax1.tick_params(axis='y', colors='lightblue')

    # Create a secondary axis
    ax2 = ax1.twinx()

    # Plot the 'rel_sector' and 'abs_sector' data on the secondary axis
    ax2.plot(abs.index, abs[selected], color='darkred', linestyle='--', label='Absolute Sector')
    ax2.plot(rel.index, rel[selected], color='darkgreen', linestyle='--', label='Relative Sector')

    # Set the y-axis label for the secondary axis
    ax2.set_ylabel('Sector Value', color='darkred')
    ax2.tick_params(axis='y', colors='darkred')

    # Set the title and legend
    ax1.set_title(f'{selected}: Relative and Absolute Regime')
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')

    canvas.draw()