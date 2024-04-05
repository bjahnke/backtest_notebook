from __future__ import annotations
from abc import ABC, abstractmethod
from copy import copy, deepcopy
from typing import Any, List


# Model
class IndicatorCollection:
    _indicators: List[Indicator]

    def __init__(self):
        self._indicators = []

    def add(self, indicator):
        self._indicators.append(indicator)
        return indicator

    def update(self, value):
        for indicator in self._indicators:
            indicator.update(value)
    
    def __iter__(self):
        return iter(self._indicators)
    
    @property
    def indicators(self):
        return deepcopy(self._indicators)


class Indicator(ABC):
    """Indicators define how calculations are made"""
    _indicators: IndicatorCollection
    __value: Any
    _price: Any
    
    def __init__(self):
        self.__value = None
        self._price = None
        self._indicators = IndicatorCollection()

    def update(self, value):
        self._indicators.update(value)
        self._price = value
        return self._update(value)

    @abstractmethod
    def _update(self, value):
        raise NotImplementedError

    @property
    def _value(self):
        return copy(self.__value)
    
    @_value.setter
    def _value(self, value):
        self.__value = value

    @property
    def value(self):
        return self._value
    
    @property
    def indicators(self):
        return self._indicators.indicators

# Implementations

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