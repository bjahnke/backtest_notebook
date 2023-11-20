from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd
from ib_insync import IB, util, Contract, BarData
from functools import wraps
from dataclasses import dataclass


class HistoricalPriceExtractor(ABC):
    @abstractmethod
    def download(self, symbols: List[str], interval: str, num_bars: int, *args, **kwargs):
        pass

    def get_data(self, symbol, interval, num_bars):
        raise NotImplementedError

    @abstractmethod
    def transform(self, *args, **kwargs):
        pass


_ib = IB()


def ib_connect(func):
    """
    A decorator function that establishes a connection to the Interactive Brokers API and passes the connection object
    to the decorated function.

    Args:
        func (callable): The function to be decorated.

    Returns:
        callable: The decorated function.

    Raises:
        ConnectionError: If the connection to the Interactive Brokers API cannot be established.

    Example:
        >>> @ib_connect
        ... def my_function(ib_conn):
        ...     # Use the ib_conn object to interact with the Interactive Brokers API
        ...     pass
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        with _ib as ib:
            ib.connect('127.0.0.1', 7496, clientId=1)
            result = func(*args, **kwargs)
        return result

    wrapper.ib = _ib
    return wrapper


class IbkrPriceExtractor(HistoricalPriceExtractor):
    interval_map = {
        '1d': '1 day',
        '1h': '1 hour',
        '1m': '1 min',
    }

    def __init__(self):
        # TODO this class can only be initialized once.
        pass

    @staticmethod
    def contracts_generator(ib, symbol: str, sec_type: str) -> List[Contract]:
        contracts = ib.reqContractDetails(Contract(symbol=symbol, secType=sec_type))
        if len(contracts) == 0:
            raise ValueError(f'No contract found for symbol={symbol}, sec_type={sec_type}')
        for contract in contracts:
            yield contract

    def _get_data(self, ib, symbol: str, interval: str, num_bars: int, sec_type, *_, **__) -> pd.DataFrame:
        interval = self.__class__.interval_map[interval]
        # assume bars are days for now
        if num_bars > 365:
            duration = '2 Y'
        else:
            duration = f'{num_bars} D'
        found = []
        for contract in self.__class__.contracts_generator(ib, symbol, sec_type):
            contract = contract.contract
            bars = ib.reqHistoricalData(
                contract=contract,
                endDateTime='',
                durationStr=duration,
                barSizeSetting=interval,
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )
            if len(bars) > 0:
                found.append((contract.exchange, contract.primaryExchange))
                break
        df = util.df(bars).rename(columns={'date': 'Date'})
        df = df.set_index('Date')
        return df

    @ib_connect
    def get_data(self, symbol: str, interval, num_bars, sec_types, *_, **__):
        return self._get_data(self.get_data.ib, symbol, interval, num_bars, sec_types)

    @ib_connect
    def download(self, symbols: List[str], interval: str, num_bars: int, sec_types, *_, **__) -> pd.DataFrame:
        if len(symbols) != len(sec_types):
            raise ValueError('symbols and sec_type must have the same length')

        price_datas = []
        for i, symbol in enumerate(symbols):
            sec_type = sec_types[i]
            price_data = self._get_data(self.download.ib, symbol, interval, num_bars, sec_type)

            # Rename columns to include symbol and sec_type
            price_data.columns = pd.MultiIndex.from_product([price_data.columns, [symbol]])

            price_datas.append(price_data)

        # Concatenate horizontally with multi-level column index
        price_data_table = pd.concat(price_datas, axis=1)
        return price_data_table

    def transform(self, *args, **kwargs):
        pass

    def _get_quote(self, ib: IB, symbol: str, sec_type: str):
        for contract in self.__class__.contracts_generator(ib, symbol, sec_type):
            quote = ib.reqTickers(contract.contract)
            if quote is not None:
                break
        return quote[0]

    @ib_connect
    def get_quote(self, symbol: str, sec_type: str):
        return self._get_quote(self.get_quote.ib, symbol, sec_type)

    def _get_quotes(self, ib: IB, symbols: List[str], sec_types: List[str]):
        contracts = []
        partial_contracts = [Contract(symbol=symb, secType=sec) for symb, sec in zip(symbols, sec_types)]
        for p_contract in partial_contracts:
            contract = ib.reqContractDetails(p_contract)
            contracts.append(contract[0].contract)
        quotes = ib.reqTickers(*contracts)
        return quotes

    @ib_connect
    def get_quotes(self, symbols: List[str], sec_types: List[str]):
        return self._get_quotes(self.get_quotes.ib, symbols, sec_types)

    def get_quote_table(self, symbols: List[str], sec_types: List[str]) -> pd.DataFrame:
        pass
