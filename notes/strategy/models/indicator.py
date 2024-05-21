from __future__ import annotations
from abc import ABC, abstractmethod
from copy import copy, deepcopy
from typing import Any, List, Literal

import numpy as np
import pandas as pd
import src.floor_ceiling_regime as fcr

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

