from abc import ABC
from notes.stats import Stats
from notes.indicator import Indicator, MoveAvgCross
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


class Strategy(Indicator, ABC):
    _log: pd.DataFrame
    _price: pd.DataFrame
    _stats: Stats

    def __init__(self):
        super().__init__()
        self._log = pd.DataFrame()
        self._price = pd.DataFrame()
        self._stats = None

    def is_ready(self) -> bool:
        return self._value is not None and len(self._log) > 0
    
    @property
    def _value(self):
        return self.__value
    
    @_value.setter
    def _value(self, value):
        """
        signals update or change when value changes,
        so update signal log when value changes
        """
        self.__value = value
        self._update_log()
        self._stats = Stats(self)
    
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
    

class VectorStrategy(Strategy):
    def __init__(self):
        super().__init__()

    def _update_log(self):
        self._log = regime_ranges(self._value)


class XOverStrat(VectorStrategy):
    """
    Strategies use indicators and price to define entry and exit logic
    """
    _xover: MoveAvgCross

    def __init__(self, slow: int, fast: int):
        super().__init__()
        self._xover = self._indicators.add(MoveAvgCross(slow, fast))

    def _update(self, value):
        """value set to 1 when fast > slow, -1 slow > fast"""
        res = self._xover.value
        res[res > 0] = 1
        res[res < 0] = -1
        self._value = res


    @property
    def xover(self):
        return self._xover
    

class Benchmark(VectorStrategy):
    """
    Benchmark strategy
    """
    def __init__(self):
        super().__init__()


    def _update(self, value):
        """benchmark strategy signal is always long"""
        self._value = pd.Series(1, index=value.index)


class Signal:
    """contains data about a signal"""
    _signal: pd.Series
    _price: pd.DataFrame

    def __init__(self, signal, price):
        self._signal = signal
        self._price = price.loc[signal.start:signal.end]
        self._stat = Stats

    @property
    def start(self):
        """bar at signal start"""
        return self._price.loc[self._signal.start]
    
    @property
    def end(self):
        """bar at signal end"""
        return self._price.loc[self._signal.end]