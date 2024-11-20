from abc import ABC
from .stats import Stats
from .indicator import Indicator
import pandas as pd

# util
def regime_ranges(signal):
    """
    Given a DataFrame and a column name, returns a DataFrame with the start and end indices of each regime in the column.

    Args:
        df (pandas.DataFrame): The DataFrame containing the regime column.
        rg_col (str): The name of the regime column.

    Returns:
        pandas.DataFrame: A DataFrame with the start and end indices of each regime in the column.
    """
    start_col = "start"
    end_col = "end"
    signal_col = "signal"
    loop_params = [(start_col, signal.shift(1)), (end_col, signal.shift(-1))]
    boundaries = {}
    for name, shift in loop_params:
        rg_boundary = signal.loc[
            ((signal == -1) & (pd.isna(shift) | (shift != -1)))
            | ((signal == 1) & ((pd.isna(shift)) | (shift != 1)))
        ]
        rg_df = pd.DataFrame(data={signal_col: rg_boundary})
        rg_df.index.name = name
        rg_df = rg_df.reset_index()
        boundaries[name] = rg_df

    boundaries[start_col][end_col] = boundaries[end_col][end_col]
    return boundaries[start_col][[start_col, end_col, signal_col]]


class Signal:
    """contains data about a signal"""
    _signal: pd.Series
    _price: pd.DataFrame

    def __init__(self, signal):
        self._signal = signal

    @property
    def start(self):
        """bar at signal start"""
        return self._price.loc[self._signal.start]
    
    @property
    def end(self):
        """bar at signal end"""
        return self._price.loc[self._signal.end]
    
    def apply(self, price: pd.DataFrame, trade_count: int):
        """apply signal to prices"""
        price = price.copy()
        price.loc[self._signal.start:self._signal.end, 'signal'] = self._signal.signal
        price.loc[self._signal.start:self._signal.end, 'trade_count'] = trade_count
        return price
    
    
class Strategy(Indicator, ABC):
    _log: pd.DataFrame
    _price: pd.Series
    _stats: Stats
    _has_warmup: bool

    def __init__(self, has_warmup=False):
        super().__init__()
        self._log = pd.DataFrame()
        self._price = pd.Series()
        self._stats = None
        self._has_warmup = has_warmup

    def is_ready(self) -> bool:
        return self._value is not None and len(self._log) > 0
    
    @property
    def _value(self):
        # not redundant, interpreter doesn't seem to pick up implementation of _value in parent class,
        # throws an error on the setter if not implemented here
        return super()._value
    
    @_value.setter
    def _value(self, value):
        """
        signals update or change when value changes,
        so update signal log when value changes
        """
        # can do super()._value = value, super() doesn't work with setters this way. https://bugs.python.org/issue14965
        self._raw_value = value
        self._update_log()
        # self._stats = Stats(self)
    
    def _update_log(self):
        raise NotImplementedError
    
    @property
    def log(self):
        return self._log

    @property
    def price(self):
        return self._price
    
    @property
    def stats(self):
        return self._stats
    
    def get_entry_bars(self, prices):
        """
        TODO
        Get rows from prices where prices.index == log.start
        return self.prices.bar.get(self.signal.start)
        """

    def get_exit_bars(self, prices):
        """
        TODO
        Get rows from prices where prices.index == log.end
        """
    
    def apply_signals(self):
        self._price = pd.DataFrame(self._price)
        for i, signal in self.log.iterrows():
            # skip first signal, counted as warmup
            if self._has_warmup and i == 0:
                continue
            self._price = Signal(signal).apply(self.price, i+1)
        self._price['signal'] = self._price['signal'].fillna(0)
        
        return self._price


class VectorStrategy(Strategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _update_log(self):
        self._log = regime_ranges(self._value)
