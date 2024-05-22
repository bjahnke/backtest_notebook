from dataclasses import dataclass, field

import pandas as pd
from ib_insync import *
import src.floor_ceiling_regime as fcr
import notes.trend_viewer
import matplotlib.pyplot as plt
from IPython.display import clear_output
from pandas.api.extensions import register_dataframe_accessor

class IbFloorCeilingStrategy:
    def __init__(self, ib, plot=True):
        self._ib = ib
        self.__plot = plot
        self._fc_indicator = FCIndicator()
        self._entry_log = pd.DataFrame()

    def run(self, symbol, sec_type, interval='1 min', duration='1 D', use_rth=True):
        contracts = self._ib.reqContractDetails(Contract(symbol=symbol, secType=sec_type, includeExpired=False))[1]
        contract = contracts.contract
        _bars = self._ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=duration,
            barSizeSetting=interval,
            whatToShow='TRADES',
            useRTH=use_rth,
            formatDate=1,
            keepUpToDate=True
        )

        _bars.updateEvent += self.onBarUpdate

        self._ib.sleep(100000)
        self._ib.cancelHistoricalData(_bars)

    def onBarUpdate(self, bars, hasNewBar):
        title = f'{bars.contract.symbol} {bars[-2].date}'
        if hasNewBar:
            is_ready = self._fc_indicator.update(bars[:-1])
            if is_ready:
                if self.__plot:
                    self._fc_indicator.plot(title)

def fc_data_from_bars(bars):
    prices = util.df(bars).reset_index().rename(columns={'index': 'bar_number'})
    tables = fcr.fc_scale_strategy_live(prices, find_retest_swing=True)
    tables.enhanced_price_data = tables.enhanced_price_data[['close']].reset_index().rename(
        columns={'index': 'bar_number'})
    return tables



class FCIndicator:
    def __init__(self, name='', period='', base_symbol=None, bench=None):
        self.Name = name
        self.WarmUpPeriod = period
        self.Value = 0

        self.price_history = {}
        self.tables = None
        self.base_symbol = base_symbol
        self.bench = bench
        self._price_history = None
        self.ready = False

    def _update_history(self, bars):
        prices = util.df(bars).reset_index().rename(columns={'index': 'bar_number'})
        self._price_history = prices

    def update(self, bars):
        self._update_history(bars[:-1])
        try:
            self.tables = fcr.fc_scale_strategy_live(self._price_history, find_retest_swing=True)
        except:
            pass
        else:
            self.ready = True
            self.Value = self.tables.regime_table.rg.iloc[-1]
        return self.ready

    # def get_history(self):
    #     history = self.price_history[self.base_symbol].copy()
    #     if self.bench is not None:
    #         bench_history = self.price_history[self.bench].copy()
    #         history.close = history.close / bench_history.close
    #     return history

    def plot(self, title):
        if self.ready is False:
            return

        plot_prices = self.tables.enhanced_price_data.copy()
        plot_prices = notes.trend_viewer.setup_trend_view_graph_simple(
            plot_prices,
            self.tables.regime_table,
            self.tables.peak_table,
            self.tables.floor_ceiling_table
        )
        notes.trend_viewer.plot(plot_prices[-300:], title)
        plt.show()
        clear_output(wait=True)

    def get_entry(self):
        if self.ready is False:
            return
        latest_regime = self.tables.regime_table.regime.get_latest()
        latest_peak = self.tables.peak_table.peak.get_latest(
            type=latest_regime.rg,
            lvl=2,
            end=self.tables.enhanced_price_data.bar_number.iloc[-1]
        )
        valid_stop_swings = self.tables.peak_table.peak.get_greater_peaks(latest_peak, type=latest_regime.rg)
        return latest_regime, latest_peak, valid_stop_swings

    # def fc_init_tables(self, history):
    #     tables = None
    #     try:
    #         tables = fcr.fc_scale_strategy_live(history, find_retest_swing=False)
    #     except Exception as e:
    #         if self.ready is True:
    #             raise e
    #         return
    #     return tables

def get_latest_regimes(regime_df):
    latest_regime_df = regime_df[regime_df['type'] == 'fc'].groupby('stock_id')['start'].max().reset_index()
    latest_regimes = regime_df.merge(latest_regime_df, left_on=['stock_id', 'start'],
                                     right_on=['stock_id', 'start'])
    return latest_regimes.groupby(['rg', 'stock_id'])['start'].max().reset_index().rename(
        columns={'start': 'max_start_1'})

def get_latest_peaks_by_regime(peak_df, regime_df):
    latest_regimes = get_latest_regimes(regime_df)
    merged_df = peak_df.merge(latest_regimes, left_on=['stock_id', 'type'], right_on=['stock_id', 'rg'])
    latest_peaks_by_regime = merged_df[merged_df['lvl'] == 2].groupby('stock_id')[
        'start'].max().reset_index().rename(columns={'start': 'latest_peaks'})
    return latest_peaks_by_regime

def get_max_stock_data(stock_data_df):
    return stock_data_df.groupby('stock_id')['bar_number'].max().reset_index().rename(
        columns={'bar_number': 'max_bar_number'})

def get_latest_signals(peak_df, regime_df, stock_data_df, stock_df):
    latest_peaks_by_regime = get_latest_peaks_by_regime(peak_df, regime_df)
    max_stock_data = get_max_stock_data(stock_data_df)

    merged_df = peak_df.merge(latest_peaks_by_regime, left_on=['start', 'stock_id'],
                              right_on=['latest_peaks', 'stock_id'])
    merged_df = merged_df.merge(max_stock_data, on='stock_id')
    merged_df = merged_df.merge(stock_df, left_on='stock_id', right_on='id')

    merged_df['signal_age'] = merged_df['max_bar_number'] - merged_df['end']
    return merged_df[merged_df['lvl'] == 2]


class BaseTableAccessor:
    required_columns = set()

    def __init__(self, pandas_obj):
        self._validate(pandas_obj)
        self._obj = pandas_obj

    @classmethod
    def _validate(cls, obj):
        cls._validate_pure(obj, cls.required_columns)

    @staticmethod
    def _validate_pure(obj, cols: set):
        obj_cols = set(obj.columns)
        if not cols.issubset(obj_cols):
            missing = cols - obj_cols
            raise AttributeError(f"DataFrame must have the following columns: {', '.join(cols)}. "
                                 f"Missing columns: {', '.join(missing)}")

    def by(self, **kwargs):
        """Return a new DataFrame with the rows filtered by the given kwargs"""
        res = self._obj.copy()
        if kwargs:
            self.__class__._validate_pure(self._obj, set(kwargs.keys()))
            q = ' and '.join(f"{k} == {v}" for k, v in kwargs.items())
            res = res.query(q)
        return res

    def get_latest(self, **kwargs):
        # Method to return the latest peak
        return self._obj.by(**kwargs).iloc[-1]


@register_dataframe_accessor("regime")
class RegimeAccessor(BaseTableAccessor):
    required_columns = {'start', 'end', 'type', 'rg'}


@register_dataframe_accessor("peak")
class PeakAccessor(BaseTableAccessor):
    required_columns = {'start', 'end', 'type', 'lvl', 'st_px', 'en_px'}

    def summary(self):
        # Method to return a summary of the peak data
        return {
            'total_peaks': self._obj.shape[0],
            'unique_stocks': self._obj['stock_id'].nunique(),
            'highest_lv': self._obj['lv'].max(),
            # Add more summary statistics as needed
        }

    def get_greater_peaks(self, peak, **kwargs):
        """
        find prior peaks with larger value
        - swing types must be equal
        - start must be prior to peak start
        - st_px must be lower than peak.st_px
        """
        obj = self.by(**kwargs)
        obj = obj.loc[
            (obj.type == peak.type) &
            (obj.start < peak.start) &
            (((obj.st_px - peak.st_px) * peak.type) < 0)
            ].copy()
        return obj


@dataclass
class FcStrategyTables:
    enhanced_price_data: pd.DataFrame
    peak_table: pd.DataFrame
    regime_table: pd.DataFrame
    floor_ceiling_table: pd.DataFrame
    valid_entries: pd.DataFrame = field(default=None)
    stop_loss_series: pd.Series = field(default=None)
    french_stop: pd.DataFrame = field(default=None)
    stats_history: pd.DataFrame = field(init=False)
    entry_table: pd.DataFrame = field(init=False)

    def get_entry(self):
        latest_regime = self.regime_table.regime.get_latest()
        latest_peak = self.peak_table.peak.get_latest(
            type=latest_regime.rg,
            lvl=2,
            end=self.enhanced_price_data.bar_number.iloc[-1]
        )
        valid_stop_swings = self.peak_table.peak.get_greater_peaks(latest_peak, type=latest_regime.rg)



