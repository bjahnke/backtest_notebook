from __future__ import annotations
from abc import ABC, abstractmethod
from copy import copy, deepcopy
from typing import Any, List, Literal

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
    

class InternalValueContainer(ABC):
    """
    A class designed to provide restricted read/write access to a variable for subclasses,
    while providing read-only access externally. This class is intended to be mixed in rather
    than directly implemented in subclasses to further discourage direct access to the variable.

    Attributes:
        __raw_value: The internal variable that stores the actual value.

    Methods:
        _value:
            Property that returns a copy of the internal variable to prevent modification via reference.
        _value.setter:
            Setter for the internal variable.
        value:
            Property that provides read-only access to the internal variable by returning a copy.
    """

    def __init__(self):
        """
        Initializes the InternalValueContainer with the internal variable set to None.
        """
        self.__raw_value = None

    @property
    def _value(self):
        """
        Used internally to return a copy of the internal variable.
        This is important because the variable may be a series or dataframe,
        and we don't want to modify the original by reference.

        :returns: A copy of the internal variable.
        """
        return copy(self.__raw_value)
    
    @_value.setter
    def _value(self, value):
        """
        Sets the internal variable to the given value.

        :param value: The value to set the internal variable to.
        """
        self.__raw_value = copy(value)

    @property
    def value(self):
        """
        Provides read-only access to the internal variable by returning a copy.

        :returns: A copy of the internal variable.
        """
        return self._value


class Indicator(InternalValueContainer):
    """Indicators define how calculations are made"""
    _indicators: IndicatorCollection
    _raw_value: Any
    _price: Any
    
    def __init__(self):
        self._price = None
        self._indicators = IndicatorCollection()

    def update(self, value):
        """copy the value to prevent modifying the original"""
        value = copy(value)
        self._indicators.update(value)
        self._price = value
        return self._update(value)

    @abstractmethod
    def _update(self, value):
        raise NotImplementedError

    @property
    def _value(self):
        """
        used to internally 
        return a copy because this may be a series or dataframe, 
        we don't want to modify the original
        
        """
        return copy(self._raw_value)
    
    @_value.setter
    def _value(self, value):
        self._raw_value = value

    @property
    def value(self):
        return self._value
    
    
    @property
    def indicators(self):
        return self._indicators.indicators
    
    def plot(self, ax, cols=None, **kwargs):
        if cols is None:
            cols = self._value.columns
        if self._value is not None:
            self._value[[cols]].plot(ax=ax, **kwargs)

# Implementations

