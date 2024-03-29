"""
Describe what this module does here:
    - load price data from db
    - scan for regimes
    - save results to db
"""
import data_manager.utils
import numpy as np
import src.floor_ceiling_regime
import regime
import pandas as pd
import scripts.env as env
from sqlalchemy import create_engine
import multiprocessing as mp
import typing as t


def regime_ranges(df, rg_col: str):
    start_col = "start"
    end_col = "end"
    loop_params = [(start_col, df[rg_col].shift(1)), (end_col, df[rg_col].shift(-1))]
    boundaries = {}
    for name, shift in loop_params:
        rg_boundary = df[rg_col].loc[
            ((df[rg_col] == -1) & (pd.isna(shift) | (shift != -1)))
            | ((df[rg_col] == 1) & ((pd.isna(shift)) | (shift != 1)))
        ]
        rg_df = pd.DataFrame(data={rg_col: rg_boundary})
        rg_df.index.name = name
        rg_df = rg_df.reset_index()
        boundaries[name] = rg_df

    boundaries[start_col][end_col] = boundaries[end_col][end_col]
    return boundaries[start_col][[start_col, end_col, rg_col]]


def load_cbpro_data(other_path, base_path):
    data_loader = data_manager.utils.DataLoader.init_from_paths(other_path, base_path)
    price_data = pd.read_csv(data_loader.history_path(), index_col=0, header=[0, 1])
    price_data = price_data.ffill()
    ticks = list(price_data.columns.levels[0].unique())
    return ticks, data_manager.utils.PriceGlob(price_data), None, None, data_loader


def new_regime_scanner(symbols, conn_str, sma_kwargs, breakout_kwargs, turtle_kwargs):
    """
    load price data from db, scan for regimes, save results to db
    :return:
    """
    # INPUTS START


    # INPUTS END
    errors = []
    tables = []
    engine = create_engine(conn_str)
    peak_tables = []
    regime_tables = []
    enhanced_price_data_tables = []

    for i, symbol in enumerate(symbols):
        data = pd.read_sql(f'SELECT * FROM stock_data WHERE symbol = \'{symbol}\'', engine)
        if data.empty:
            print(f'No data for {symbol}')
            continue
        # print symbol and timestamp to track progress
        print(f'{i}.) {symbol} {pd.Timestamp.now()}')
        price_data = data.loc[data.symbol == symbol]
        relative_data = price_data.loc[data.is_relative == True].reset_index(drop=True)
        absolute_data = price_data.loc[data.is_relative == False].reset_index(drop=True)
        try:
            relative_tables = src.floor_ceiling_regime.fc_scale_strategy_live(price_data=relative_data)
            absolute_tables = src.floor_ceiling_regime.fc_scale_strategy_live(price_data=absolute_data)

        except (regime.NotEnoughDataError, src.floor_ceiling_regime.NoEntriesError) as e:
            # store symbol and error type
            errors.append((symbol, type(e)))
        except KeyError as e:
            errors.append((symbol, type(e)))
        else:
            relative_tables = format_tables(relative_tables, symbol, is_relative=False)
            absolute_tables = format_tables(absolute_tables, symbol, is_relative=True)

            peak_tables.extend([relative_tables.peak_table, absolute_tables.peak_table])
            regime_tables.extend([
                relative_tables.regime_table,
                absolute_tables.regime_table,
                init_trend_table(relative_tables.enhanced_price_data, sma_kwargs, breakout_kwargs, turtle_kwargs),
                init_trend_table(absolute_tables.enhanced_price_data, sma_kwargs, breakout_kwargs, turtle_kwargs)
            ])
            enhanced_price_data_tables.extend([relative_tables.enhanced_price_data, absolute_tables.enhanced_price_data])

    pd.concat(peak_tables).reset_index(drop=True).to_sql('peak', engine, if_exists='append', index=False)
    pd.concat(regime_tables).reset_index(drop=True).to_sql('regime', engine, if_exists='append', index=False)
    pd.concat(enhanced_price_data_tables).reset_index(drop=True).to_sql('enhanced_price', engine, if_exists='append', index=False)


def turtle_trader(df, _h, _l, slow, fast):
    """
    #### turtle_trader(df, _h, _l, slow, fast) ####
    _slow: Long/Short direction
    _fast: trailing stop loss
    """
    _slow = regime_breakout(df, _h, _l, window=slow)
    _fast = regime_breakout(df, _h, _l, window=fast)
    turtle = pd.Series(index=df.index,
                       data=np.where(_slow == 1, np.where(_fast == 1, 1, 0),
                                     np.where(_slow == -1, np.where(_fast == -1, -1, 0), 0)))
    return turtle


def regime_sma(df, _c, st, lt):
    """
    #### regime_sma(df,_c,st,lt) ####
    bull +1: sma_st >= sma_lt , bear -1: sma_st <= sma_lt
    """
    sma_lt = df[_c].rolling(lt).mean()
    sma_st = df[_c].rolling(st).mean()
    rg_sma = np.sign(sma_st - sma_lt)
    return rg_sma


def regime_breakout(df, _h, _l, window):
    """
    #### regime_breakout(df,_h,_l,window) ####
    :param df:
    :param _h:
    :param _l:
    :param window:
    :return:
    """

    hl = np.where(df[_h] == df[_h].rolling(window).max(), 1,
                  np.where(df[_l] == df[_l].rolling(window).min(), -1, np.nan))
    roll_hl = pd.Series(index=df.index, data=hl).fillna(method='ffill')
    return roll_hl


def init_trend_table(price_data, sma_kwargs, breakout_kwargs, turtle_kwargs):
    """
    #### init_trend_table(price_data, sma_kwargs, breakout_kwargs, turtle_kwargs) ####
    initialize trend table with sma, breakout, turtle
    :param price_data:
    :param sma_kwargs:
    :param breakout_kwargs:
    :param turtle_kwargs:
    :return:
    """
    _c = 'close'
    _h = 'high'
    _l = 'low'
    # 'sma' + str(_c)[:1] + str(sma_kwargs['st']) + str(sma_kwargs['lt'])
    data = price_data.copy()
    data['rg'] = regime_sma(price_data, _c, sma_kwargs['st'], sma_kwargs['lt'])
    sma_ranges = regime_ranges(data, 'rg')
    sma_ranges['type'] = 'sma'
    # + str(_h)[:1] + str(_l)[:1] + str(breakout_kwargs['slow'])
    data['rg'] = regime_breakout(price_data, _h, _l, breakout_kwargs['window'])
    bo_ranges = regime_ranges(data, 'rg')
    bo_ranges['type'] = 'bo'
    #  + str(_h)[:1] + str(turtle_kwargs['fast']) + str(_l)[:1] + str(breakout_kwargs['slow'])
    data['rg'] = turtle_trader(price_data, _h, _l, breakout_kwargs['slow'], turtle_kwargs['fast'])
    tt_ranges = regime_ranges(data, 'rg')
    tt_ranges['type'] = 'tt'
    # create dataframe with sma, tt, bo as columns
    trend_table = pd.concat([sma_ranges, bo_ranges, tt_ranges])
    trend_table['symbol'] = price_data['symbol'].iloc[0]
    trend_table['is_relative'] = price_data['is_relative'].iloc[0]
    return trend_table


def regime_scanner_mp(args):
    return new_regime_scanner(*args)


def format_tables(tables, symbol, is_relative):
    tables.peak_table['symbol'] = symbol
    tables.peak_table['is_relative'] = is_relative
    tables.enhanced_price_data['symbol'] = symbol
    tables.enhanced_price_data['is_relative'] = is_relative
    tables.regime_table['symbol'] = symbol
    tables.regime_table['is_relative'] = is_relative
    return tables


def split_list(alist, wanted_parts=1):
    length = len(alist)
    return [
        alist[i * length // wanted_parts: (i + 1) * length // wanted_parts]
        for i in range(wanted_parts)
    ]


def init_multiprocess(analysis_function, symbols: t.List[str], *args):
    """
    run analysis function in parallel
    :param analysis_function:
    :param symbols:
    :param args:
    :return:
    """
    # set up multiprocessing with pool
    with mp.Pool(None) as p:
        # run analysis for each symbol
        results = p.map(
            analysis_function,
            [(symbol,) + args for symbol in split_list(symbols, mp.cpu_count() - 1)]
        )
    # flatten results
    return results


def main(multiprocess: bool = False):
    """
    load price data from db, scan for regimes, save results to db
    :param multiprocess:
    :return:
    """
    trend_args = (
        {  # rg sma args
            'st': 50,
            'lt': 200
        },
        {  # rg breakout args
            'slow': 200,
            'window': 100
        },
        {  # rg turtle args
            'fast': 50
        },
    )
    # get symbols from db
    connection_string = "postgresql://bjahnke71:8mwXTCZsA6tn@ep-spring-tooth-474112-pooler.us-east-2.aws.neon.tech/historical-stock-data"
    engine = create_engine(connection_string, echo=True)
    symbols = pd.read_sql('SELECT symbol FROM stock_data', engine)
    engine.execute('DROP TABLE IF EXISTS peak')
    engine.execute('DROP TABLE IF EXISTS enhanced_price')
    engine.execute('DROP TABLE IF EXISTS regime')
    # data.symbol to list of unique symbols
    symbols = symbols.symbol.unique().tolist()

    if multiprocess:
        init_multiprocess(regime_scanner_mp, symbols, connection_string, *trend_args)
    else:
        new_regime_scanner(symbols, connection_string, *trend_args)

import tda_access.access as taa
if __name__ == '__main__':
    """
    rebuild scan data 
    run after updating scanner code to view results in notebook
    """
    td_client = taa.TdBrokerClient.init_from_json('..\\data_args\\credentials.json')
    client = td_client.client.ensure_updated_refresh_token()
    # main(multiprocess=True)
