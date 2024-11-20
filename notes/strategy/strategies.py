from .indicators import TradingRange, MoveAvgCross, BollingerBand
from .logic import VectorStrategy
import pandas as pd

class XOverStrat(VectorStrategy):
    """
    Strategies use indicators and price to define entry and exit logic
    """
    _xover: MoveAvgCross

    def __init__(self, slow: int, fast: int):
        super().__init__(has_warmup=True)
        self._xover = self._indicators.add(MoveAvgCross(slow, fast))

    def _update(self, value):
        """value set to 1 when fast > slow, -1 slow > fast"""
        res = self._xover.value
        res[
            (res > 0)
        ] = 1
        res[
            (res < 0)
        ] = -1
        self._value = res.shift()


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
    

class BollingerMeanReversion(VectorStrategy):
    _bb: BollingerBand

    def __init__(self, window: int, n_std: int):
        super().__init__(has_warmup=True)
        self._bb = self._indicators.add(BollingerBand(window, n_std))

    def _update(self, value):
        """
        value set to 1 when price > upper band, -1 price < lower band
        """
        res = value.copy()
        res.loc[
            (value > self._bb.value.upper)
        ] = -1
        res.loc[
            (value < self._bb.value.lower)
        ] = 1
        self._value = res.shift()

    @property
    def bb(self):
        return self._bb
    

class Custom(VectorStrategy):
    def __init__(self, indicators):
        super().__init__()
        [self._indicators.add(indicator) for indicator in indicators]


    def _update(self, value):
        res = value.copy()
        res.loc[
            (value > 0)
        ] = 1
        self._value = res.shift()


class TradingRangeBreakout(VectorStrategy):
    def __init__(self, high_band_pct, low_band_pct, window=233):
        super().__init__(has_warmup=True)
        self._trading_range = self._indicators.add(TradingRange(high_band_pct, low_band_pct, window))

    @property
    def trading_range(self):
        return self._trading_range

    def _update(self, value):
        res = value.copy()
        # Set res to 1 if value is above the upper band
        res.loc[
            (value > self._trading_range.value.upper)
        ] = 1
        # Set res to -1 if value is below the lower band
        res.loc[
            (value < self._trading_range.value.lower)
        ] = -1
        # Set res to 0 if value is between the upper and lower bands
        res.loc[
            (value <= self._trading_range.value.upper) & (value >= self._trading_range.value.lower)
        ] = 0
        self._value = res