import pandas as pd
from src.regime.utils import (
    retest_from_latest_base_swing,
    find_all_retest_swing,
    add_peak_regime_data,
)

import matplotlib.pyplot as plt

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
def plot(_stock_data, title, entries=False, secondary_y=None, style_map=None, legend=False, figsize=None):
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
        'band_24': 'y--',
        'band_76': 'y--',
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
        ax = sd[
            style_map.keys()
            ].plot(
                legend=legend, 
                style=list(style_map.values()), 
                secondary_y=secondary_y, 
                figsize=figsize, 
                title=title
                )
        return ax
    except KeyError:
        pass

def setup_trend_view_graph(stock_data, regime_data, peak_data, fc_data):
    peak_data.lvl = peak_data.lvl.astype(int)
    
    try: 
        # wrapped in try because these values might be datetime/string
        fc_data.rg_ch_date = fc_data.rg_ch_date.astype(int)
        fc_data.fc_date = fc_data.fc_date.astype(int)
    except:
        pass
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
    try: 
        # wrapped in try because these values might be datetime/string
        fc_data.rg_ch_date = fc_data.rg_ch_date.astype(int)
        fc_data.fc_date = fc_data.fc_date.astype(int)
    except:
        pass
    _stock_data = add_fc_data(_stock_data, fc_data)
    # TODO due to a bug in add_fc_data, we have to drop duplicates
    _stock_data = _stock_data.loc[~_stock_data.bar_number.duplicated(keep='last')].copy()
    return _stock_data


def add_regime_data(_price_data, _regime_data):
    for index, row in _regime_data.iterrows():
        _price_data.loc[row.start:row.end, row.type] = row.rg
    return _price_data


def add_fc_data(_stock_data, _fc_data):
    # TODO add column to fc_data to indicate regime change type (floor_ceiling or breakout/breakdown)
    local_fc_data = _fc_data.drop_duplicates(subset=['fc_date']).drop_duplicates(subset=['rg_ch_date'])
    fc_val_table = local_fc_data[['fc_val', 'fc_date']]
    if 'bar_number' not in _stock_data.columns:
        _stock_data = _stock_data.reset_index().rename(columns={'index': 'bar_number'})
    _stock_data = _stock_data.drop_duplicates(subset=['bar_number'])  # Drop duplicates based on bar_number
    _stock_data = _stock_data.merge(
        fc_val_table, how='left', left_on='bar_number', right_on='fc_date')

    rg_change_table = local_fc_data[['rg_ch_val', 'rg_ch_date']]
    _stock_data = _stock_data.merge(
        rg_change_table, how='left', left_on='bar_number', right_on='rg_ch_date')
    _stock_data.rg_ch_val = _stock_data.rg_ch_val.ffill()
    return _stock_data


def addBand(price, window):
    price['rolling_max'] = price.close.rolling(window=window).max()
    price['rolling_min'] = price.close.rolling(window=window).min()
    price['trading_range'] = (price.rolling_max - price.rolling_min)
    price['trading_range_lo_band'] = price.rolling_min + price.trading_range * .61
    price['trading_range_hi_band'] = price.rolling_min + price.trading_range * .40
    price['band_24'] = price.rolling_min + price.trading_range * .24
    price['band_76'] = price.rolling_min + price.trading_range * .76
    return price, window


def addBandExpanding(price, window):
    price['rolling_max'] = 0
    rm = price.close
    price['rolling_max'] = price.close.expanding(window).max()
    price['rolling_min'] = price.close.expanding(window).min()
    price['trading_range'] = (price.rolling_max - price.rolling_min)
    price['trading_range_lo_band'] = price.rolling_min + price.trading_range * .61
    price['trading_range_hi_band'] = price.rolling_min + price.trading_range * .40
    price['band_24'] = price.rolling_min + price.trading_range * .24
    price['band_76'] = price.rolling_min + price.trading_range * .76
    return price, window





def addBandAggregateSlice(price, peak_window, peaks):
    peaks.start = peaks.start.astype(int)
    peaks.end = peaks.end.astype(int)
    if len(peaks) < peak_window:
        return addBand(price, len(price))
    
    major_peaks = peaks[peaks.lvl == 3].sort_values('end').reset_index(drop=True)

    def addBand(p, window, index_slice):
        p.loc[-window:, 'rolling_max'] = p.close.rolling(window=window).max().loc[-window:]
        p.loc[-window:, 'rolling_min'] = p.close.rolling(window=window).min()
        p.loc[-window:, 'trading_range'] = (p.rolling_max - p.rolling_min)
        p.loc[-window:, 'trading_range_lo_band'] = p.rolling_min + p.trading_range * .61
        p.loc[-window:, 'trading_range_hi_band'] = p.rolling_min + p.trading_range * .40
        p.loc[-window:, 'band_24'] = p.rolling_min + p.trading_range * .24
        p.loc[-window:, 'band_76'] = p.rolling_min + p.trading_range * .76
        return p

    # reduce by one becuase peaks are inclusive (0-4 is 5 peaks)
    peak_window = peak_window -1
    for index in range(peak_window, len(major_peaks)):
        # look back x peaks to get the start of the window (-1 used because peaks inclusive 0-4 is 5 peaks)
        window_start = int(major_peaks.iloc[peak_window].start)
        # look ahead to the next peak's discovery or the end of the data for the end of the window
        window_end = int(price.index[-1]) if index == len(major_peaks) - 1 else int(major_peaks.iloc[index + 1].end - 1)
        index_slice = slice(window_start, window_end)
        price, window = addBand(price, window_end - window_start + 1, index_slice)
    
    # Ensure no duplicate indexes
    print('duplicates?', price.index.duplicated().sum())
    price = price[~price.index.duplicated(keep='first')]
    
    return price, window


def updateBandSingle(price, window):
    # Ensure the DataFrame has the necessary columns initialized
    if 'rolling_max' not in price.columns:
        price['rolling_max'] = pd.Series(dtype='float64')
    if 'rolling_min' not in price.columns:
        price['rolling_min'] = pd.Series(dtype='float64')
    if 'trading_range' not in price.columns:
        price['trading_range'] = pd.Series(dtype='float64')
    if 'trading_range_lo_band' not in price.columns:
        price['trading_range_lo_band'] = pd.Series(dtype='float64')
    if 'trading_range_hi_band' not in price.columns:
        price['trading_range_hi_band'] = pd.Series(dtype='float64')

    # Get the latest index
    latest_index = price.index[-1]

    # Calculate rolling max and min for the latest window
    rolling_window = price['close'].iloc[-window:]
    rolling_max = rolling_window.max()
    rolling_min = rolling_window.min()

    # Update the latest values in the DataFrame
    price.at[latest_index, 'rolling_max'] = rolling_max
    price.at[latest_index, 'rolling_min'] = rolling_min
    price.at[latest_index, 'trading_range'] = rolling_max - rolling_min
    price.at[latest_index, 'trading_range_lo_band'] = rolling_min + (rolling_max - rolling_min) * 0.61
    price.at[latest_index, 'trading_range_hi_band'] = rolling_min + (rolling_max - rolling_min) * 0.40
    return price


def addBandAggregatePeakConcat(price, peak_window, peaks, fast_band=False):
    assert peak_window > 0, 'peak_window must be greater than 0'

    peaks.start = peaks.start.astype(int)
    peaks.end = peaks.end.astype(int)
    if len(peaks) < peak_window:
        return addBand(price, len(price))
    
    major_peaks = peaks[peaks.lvl == 3].sort_values('end').reset_index(drop=True)
    # major_peaks_forward_look = major_peaks
    # major_peaks_backward_look = major_peaks.sort_values('start').reset_index(drop=True)
    band_periods = []

    peak_window = peak_window - 1
    for index in range(peak_window, len(major_peaks)):
        window_start = int(major_peaks.iloc[index - peak_window:index].start.min())
        window_end = int(price.index[-1]) if index == len(major_peaks) - 1 else int(major_peaks.iloc[index + 1].end - 1)
        price_slice = price[window_start: window_end]
        band_window = int(major_peaks.iloc[index].end - window_start + 1)
        price_slice, band_window = addBandExpanding(price_slice.copy(), band_window)
        if index != peak_window:
            price_slice: pd.DataFrame = price_slice.dropna(subset=['rolling_max'])

        band_periods.append(price_slice)

    # Concatenate all band periods
    result = pd.concat(band_periods)
    
    # Ensure no duplicate indexes
    result = result[~result.index.duplicated(keep='first')]
    
    return result, band_window


def plot_fc_tables(title, strat, peak_window, plot_window, band_window, bandFunc, figsize=None, fast_band=False):
    tables = strat.indicators[0].value
    plot_prices = tables.enhanced_price_data.copy()
    
    plot_prices = setup_trend_view_graph_simple(
        plot_prices, 
        tables.regime_table, 
        tables.peak_table, 
        tables.floor_ceiling_table
    )
    # set strat index to match plot_prices
    if peak_window:
        plot_prices, band_window = bandFunc(plot_prices, peak_window, tables.peak_table)
    else:
        plot_prices, band_window = bandFunc(plot_prices, band_window)
    

    plot_prices = plot_prices[-plot_window:]
    
    # print current value of upper and lower bands
    print(f'Upper band: {plot_prices.trading_range_lo_band.iloc[-1]}')
    print(f'Lower band: {plot_prices.trading_range_hi_band.iloc[-1]}')
    print(f'Band 24: {plot_prices.band_24.iloc[-1]}')
    print(f'Band 76: {plot_prices.band_76.iloc[-1]}')
    ax = plot(plot_prices, title, figsize=figsize)

    ax.plot(plot_prices.index, plot_prices['rolling_max'], label='Rolling Max', color='lightblue')
    ax.plot(plot_prices.index, plot_prices['rolling_min'], label='Rolling Min', color='lightgreen')

    # highlight grey portion of graph to focus on data used for bands to forsee future band movement
    last_index = len(plot_prices) - band_window
    start_highlight = 0
    ax.axvspan(plot_prices.index[start_highlight], plot_prices.index[last_index], color='lightgrey', alpha=0.5)

    return plot_prices, ax

class IBRunManager:
    def __init__(self, ib, Contract, strategy, indicator, util, clear_output):
        self.ib = ib
        self.Contract = Contract
        self.strategy = strategy
        self.indicator = indicator
        self.util = util
        self.clear_output = clear_output
        self._bars = None
        self._ax = None

    def run(
        self,
        symbol, 
        sec_type, 
        bandFunc,
        interval='1 min', 
        duration='1 D', 
        use_rth=True, 
        keep_up_to_date=True, 
        band_window=256, 
        plot_window=600, 
        peak_window=None,
        figsize=None,
        fast_band=False
    ):
        if figsize is None:
            figsize = (10, 10)

        ib = self.ib
        Contract = self.Contract
        strategy = self.strategy
        indicator = self.indicator
        util = self.util
        clear_output = self.clear_output
        if keep_up_to_date:
            if self._bars is not None:
                ib.cancelHistoricalData(self._bars)

        contracts = ib.reqContractDetails(Contract(localSymbol=symbol, secType=sec_type, includeExpired=False))[0]
        contract = contracts.contract
        history_kwargs = {
            "contract": contract,
            "endDateTime": '',
            "durationStr": duration,
            "barSizeSetting": interval,
            "whatToShow": 'TRADES',
            "useRTH": use_rth,
            "formatDate": 1,
        }
        first_run_bars = ib.reqHistoricalData(**history_kwargs)
        _bars = ib.reqHistoricalData(keepUpToDate=keep_up_to_date, **history_kwargs)
        # indicator.TradingRange(high_band_pct=.40, low_band_pct=.61, window=band_window),
        strat = strategy.Custom(
            indicators=[
                indicator.Regime(),
            ]
        )
        
        def onBarUpdate(bars, hasNewBar):
            if hasNewBar:
                self._bars = bars
                title = f'{bars.contract.symbol} {bars[-1].date}'
                # exclude the last bar because it is not complete
                prices = util.df(bars)
                # Exclude latest bar if it is not complete
                prices = prices
                title = f'{bars.contract.symbol} {bars[-2].date}'
                prices.index = prices.date 
                prices = prices.drop(columns=['date'])
                strat.update(prices.close.copy())
                price_data, self._ax = plot_fc_tables(
                    title, strat, peak_window, plot_window, band_window, bandFunc, figsize=figsize, fast_band=fast_band)
                plt.show()

            
        if keep_up_to_date:

            onBarUpdate(first_run_bars, True)
            
            _bars.updateEvent += onBarUpdate
            ib.sleep(100000)
            
        else:
            onBarUpdate(_bars, True)
        

def run_profile(
    deps,
    symbol, 
    sec_type, 
    bandFunc,
    interval='1 min', 
    duration='1 D', 
    use_rth=True, 
    keep_up_to_date=True, 
    band_window=256, 
    plot_window=600, 
    peak_window=None,
    figsize=None,
    fast_band=False,
    current_subscription=None
):
    if current_subscription is not None:
        ib.cancelHistoricalData(current_subscription)

    if figsize is None:
        figsize = (10, 10)
    (
        ib,
        Contract,
        strategy,
        indicator,
        util,
        clear_output,
    ) = deps
    band_window = band_window
    contracts = ib.reqContractDetails(Contract(localSymbol=symbol, secType=sec_type, includeExpired=False))[0]
    contract = contracts.contract
    history_kwargs = {
        "contract": contract,
        "endDateTime": '',
        "durationStr": duration,
        "barSizeSetting": interval,
        "whatToShow": 'TRADES',
        "useRTH": use_rth,
        "formatDate": 1,
    }
    
    if keep_up_to_date:
        first_run_bars = ib.reqHistoricalData(**history_kwargs)

    _bars = ib.reqHistoricalData(keepUpToDate=keep_up_to_date, **history_kwargs)

    # indicator.TradingRange(high_band_pct=.40, low_band_pct=.61, window=band_window),
    strat = strategy.Custom(
        indicators=[
            indicator.Regime(),
        ]
    )
    
    def onBarUpdate(bars, hasNewBar):
        
        if hasNewBar:
            title = f'{bars.contract.symbol} {bars[-1].date}'
            # exclude the last bar because it is not complete
            prices = util.df(bars)
            # Exclude latest bar if it is not complete
            prices = prices
            title = f'{bars.contract.symbol} {bars[-2].date}'
            prices.index = prices.date 
            prices = prices.drop(columns=['date'])
            strat.update(prices.close.copy())
            price_data, ax = plot_fc_tables(
                title, strat, peak_window, plot_window, band_window, bandFunc, figsize=figsize, fast_band=fast_band)
            plt.show()

            clear_output(wait=True)

        
    if keep_up_to_date:
        onBarUpdate(first_run_bars, True)
        
        _bars.updateEvent += onBarUpdate
        ib.sleep(100000)
        # ib.cancelHistoricalData(_bars)
    else:
        onBarUpdate(_bars, True)

    return _bars