from typing import Literal
from .logic.indicator import Indicator
import src.floor_ceiling_regime as fcr
import pandas as pd

class MoveAvg(Indicator):
    _window: int

    def __init__(self, window: int):
        assert window > 0
        super().__init__()
        self._window = window

    def __get__(self):
        return self._value
    
    def _update(self, value):
        self._value = value.rolling(self._window).mean()
        return self._value
    
    @property
    def window(self):
        return self._window


class MoveAvgCross(Indicator):
    _fast: MoveAvg
    _slow: MoveAvg

    def __init__(self, fast: int, slow: int):
        assert fast < slow
        super().__init__()
        self._slow = self._indicators.add(MoveAvg(slow))
        self._fast = self._indicators.add(MoveAvg(fast))

    def _update(self, value):
        self._value = self._fast.update(value) - self._slow.update(value)
        return self._value
    
    @property
    def fast(self):
        return self._fast
    
    @property
    def slow(self):
        return self._slow
    

class BollingerBand(Indicator):
    _window: int
    _std: int
    _middle: MoveAvg

    def __init__(self, window: int = 20, std: int = 2):
        assert window > 0
        assert std > 0
        super().__init__()
        self._window = window
        self._std = std
        self._middle = self._indicators.add(MoveAvg(window))

    def _update(self, value):
        std = value.rolling(self._window).std() * self._std
        self._value = pd.DataFrame({
            'upper': self._middle.value + std, 
            'lower': self._middle.value - std
        })
        return self._value
    
    @property
    def window(self):
        return self._window
    
    @property
    def std(self):
        return self._std
    
    @property
    def middle(self):
        return self._middle.value
    
    @property
    def upper(self):
        return self._value['upper']
    
    @property
    def lower(self):
        return self._value['lower']
    

class TradingRange(Indicator):
    def __init__(self, high_band_pct=.40, low_band_pct=.61, window=200):
        assert 0 < high_band_pct < 1, 'High band must be between 0 and 1'
        assert 0 < low_band_pct < 1, 'Low band must be between 0 and 1'
        assert high_band_pct > low_band_pct, 'High band must be greater than low band'
        super().__init__()
        self._high_band_pct = high_band_pct
        self._low_band_pct = low_band_pct
        self._window = window

    def _update(self, value):
        rolling_max = value.rolling(self._window).max()
        rolling_min = value.rolling(self._window).min()
        trading_range = (rolling_max - rolling_min)  
        value = pd.DataFrame({
            'upper': rolling_min + trading_range * self._high_band_pct,
            'lower': rolling_min + trading_range * self._low_band_pct,
            'band_24': rolling_min + trading_range * .24,
            'band_76': rolling_min + trading_range * .76,
            'min': rolling_min,
            'max': rolling_max
        })
        return value
    
    @property
    def upper(self):
        return self._value['upper']
    
    @property
    def lower(self):
        return self._value['lower']
    
    @property
    def high_band_pct(self):
        return self._high_band_pct
    
    @property
    def low_band_pct(self):
        return self._low_band_pct
    
    @property
    def window(self):
        return self._window
    

class Regime(Indicator):
    _threshold: float
    _direction: Literal[-1, 1]

    def _update(self, value):
        value = value.reset_index(drop=True).reset_index().rename(columns={'index': 'bar_number'})
        self._value = fcr.fc_scale_strategy_live(value, find_retest_swing=False)
        return self._value
    
    @property
    def threshold(self):
        return self._threshold
    
    