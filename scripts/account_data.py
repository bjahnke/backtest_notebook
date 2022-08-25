from __future__ import annotations

import json
import typing as t

import numpy as np
import pandas as pd
import tda_access.access as taa
import datetime
import data_manager.utils as dmu
import src.floor_ceiling_regime
import regime


class PdStorageHandler:
    """
    utility class for loading and writing multple dataframes
    to/from a single workbook
    """
    def __init__(self, **kwargs: pd.DataFrame):
        self._tables = self.__class__._get_tables(kwargs)

    @staticmethod
    def _get_tables(var_dict: t.Dict[str, t.Any]) -> t.List[str]:
        """
        Helps this class find tables dynamically from input
        :param var_dict: dict of vars passed from subclass
        :return: only a list of dataframes
        """
        res = []
        for key, val in var_dict.items():
            if isinstance(val, pd.DataFrame):
                res.append(key)
        return res

    @property
    def tables(self):
        """get the current reference to tables"""
        return {name: self.__dict__[name] for name in self._tables}

    @staticmethod
    def read_excel(path) -> t.Dict[str, pd.DataFrame]:
        obj = pd.read_excel(path, sheet_name=None, index_col=0)
        return obj

    def to_excel(self, path):
        with pd.ExcelWriter(path, engine='xlsxwriter') as writer:
            for name, table in self.tables.items():
                table.to_excel(excel_writer=writer, sheet_name=name)


class TransactionTables(PdStorageHandler):
    data: pd.DataFrame
    fees: pd.DataFrame
    transaction: pd.DataFrame
    position: pd.DataFrame
    path: str

    def __init__(self, data, fees, transaction, position):
        kwargs = locals()
        del kwargs['self']
        super().__init__(**kwargs)
        self.data = data
        self.fees = fees
        self.transaction = transaction
        self.position = position

    @classmethod
    def from_excel(cls, path):
        data = cls.read_excel(path)
        obj = cls(**data)
        obj.path = path

        obj.position.quantity = obj.position.quantity.astype('float64')
        return obj

    @classmethod
    def parse_df(cls, nested_table: pd.DataFrame, positions):
        data_table = nested_table
        data_table.orderDate = np.where(
            pd.isna(data_table.orderDate), data_table.transactionDate, data_table.orderDate
        )
        data_table = data_table.sort_values(by='orderDate').reset_index(drop=True)
        fees_table = pd.DataFrame(list(data_table['fees']))
        transaction_table = pd.DataFrame(list(data_table['transactionItem']))

        transaction_table.loc[pd.notna(transaction_table.instrument), 'symbol'] = (
            pd.DataFrame(list(transaction_table.instrument.dropna())).symbol.values
        )
        transaction_table = transaction_table.drop(columns='instrument')

        data_table = data_table.drop(columns=['fees', 'transactionItem'])

        return cls(
            data_table,
            fees_table,
            transaction_table,
            positions
        )

    def _update(self, new_tx: TransactionTables):
        """

        :param new_tx:
        :return:
        """
        self.data = pd.concat([self.data, new_tx.data]).reset_index(drop=True)
        self.fees = pd.concat([self.fees, new_tx.fees]).reset_index(drop=True)
        self.transaction = pd.concat([self.transaction, new_tx.transaction]).reset_index(drop=True)

    def update(self, nested_table: pd.DataFrame, positions: pd.DataFrame):
        new_data = nested_table.loc[nested_table.orderDate > self.data.orderDate.iloc[-1]]
        updated = False
        if not new_data.empty:
            new_tx_tables = self.__class__.parse_df(new_data, positions)
            self._update(new_tx_tables)
            updated = True

        # TODO update if symbols differ
        if not self.position[['symbol', 'quantity']].equals(positions[['symbol', 'quantity']]):
            self.position = positions
            self.tables['position'] = positions
            updated = True

        if updated:
            self.to_excel(self.path)

    def get_trades(self):
        return self.transaction.loc[
            (self.transaction.symbol != np.nan) &
            (self.transaction.symbol != 'MMDA1')
        ]

    def get_open_position_trades(self):
        return self.transaction.loc[
            self.transaction.symbol.isin(self.position.symbol)
        ]


def main_merge(client):
    """
    merge local transactions with any new transactions pulled from api, store it locally
    :return:
    """
    local_path = '..\\data\\transaction_data_local.xlsx'
    tx_local = TransactionTables.from_excel(local_path)
    tx_base, positions = get_base_tx_table(client)
    tx_local.update(tx_base, positions)
    tx_local.to_excel(local_path)


def get_base_tx_table(td_client) -> t.Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Downloads account/transaction data from TD. Converts to dataframes.
    Transaction data will still be nested
    :return:
    """
    _account = td_client.account_info()
    with open('..\\data\\account_info.json', 'w') as fp:
        json.dump(_account.account_data, fp, indent=2)

    # get/update position table
    _pos = _account.get_position_table()

    # get transaction history
    _tx_resp = td_client.get_transactions()
    _tx_info = _tx_resp.json()
    if len(_tx_info) == 0:
        print('break')
    data_table = pd.DataFrame.from_dict(_tx_info)
    return data_table, _pos


def refresh_local_transactions():
    TransactionTables.parse_df(*get_base_tx_table()).to_excel('..\\data\\transaction_data_local.xlsx')


def main_analyze_portfolio(multiprocess: False):
    """
    run analysis on portfolio constituents
    :return:
    """

    # init client and tables
    td_client = taa.TdBrokerClient.init_from_json('..\\data_args\\credentials.json')
    main_merge(td_client)
    tx_tables = TransactionTables.from_excel('..\\data\\transaction_data_local.xlsx')
    # get price history
    symbols = list(tx_tables.position.symbol.values)

    ph_params = {
        'interval': 1,
        'interval_type': 'd',
        'start': datetime.datetime.utcnow() - datetime.timedelta(days=365*2)
    }
    bench_id = 'SPY'
    price_histories = td_client.download_price_history(
        symbols,
        **ph_params
    )
    bench = td_client.price_history(
        symbol=bench_id,
        **ph_params
    )
    with open('..\\data_args\\scan_args.json') as fp:
        scan_args = json.load(fp)

    expected_exceptions = (regime.NotEnoughDataError, src.floor_ceiling_regime.NoEntriesError)

    strategy_args = scan_args
    if multiprocess:
        res = dmu.mp_analysis(
            ticks_list=symbols,
            _scanner=dmu.mp_regime_analysis,
            scan_args=(
                dmu.PriceGlob(price_histories),
                bench,
                bench_id,
                strategy_args,
                src.floor_ceiling_regime.fc_scale_strategy_live,
                expected_exceptions
            ),
        )
    else:
        res = dmu.regime_analysis(
            _ticks=symbols,
            price_glob=dmu.PriceGlob(price_histories),
            bench=bench,
            benchmark_id=bench_id,
            scan_params=strategy_args,
            strategy_simulator=src.floor_ceiling_regime.fc_scale_strategy_live,
            expected_exceptions=expected_exceptions,
        )
    return res, tx_tables


def check_trend_congruency(
        position_table: pd.DataFrame, portfolio_scan:
        t.Dict[str, src.floor_ceiling_regime.FcStrategyTables]
) -> pd.DataFrame:
    """
    Check if trend is different than current position direction
    :param position_table: 
    :param portfolio_scan: 
    :return: table of symbols and quantity to close
    """
    res = []
    for symbol, scan_data in portfolio_scan.items():
        # TODO what to do if no regime?
        current_regime = scan_data.regime_table.rg.iloc[-1]
        position_data = position_table.loc[position_table.symbol == symbol]
        position_quantity = position_data.quantity.iat[0]
        if current_regime * position_quantity < 0:
            res.append({'symbol': symbol, 'quantity': position_quantity*-1})

    if len(res) > 0:
        res = pd.DataFrame.from_dict(res)
    else:
        res = pd.DataFrame(columns=['symbol', 'quantity'])
    return res


if __name__ == '__main__':
    # refresh_local_transactions()
    # main_merge()
    # _tx_tables.to_excel('..\\data\\transaction_data_local.xlsx')
    _scan_res, _tx_tables = main_analyze_portfolio(multiprocess=False)
    _close_pos = check_trend_congruency(_tx_tables.position, _scan_res)

    print('d')
    # TODO
    # - with given position data (open positions), look for closing orders
    # 1.) closing order by regime change -> close entire position
    #
    # create order table generated from system
    # 1.) assume new position
    # 2.) include symbol, size, stop loss, (direction?)
    # 3.) manually executing trade by selecting an index and an internal function
    #       this function executes the order and stores the data in a local table
    #       - probably need to match broker trade data with local data

    # TODO generate closing orders for existing positions

    # _receive_conn, _send_conn = mp.Pipe(duplex=True)
    # _stream_process = mp.Process(target=stream_app, args=(_inputs['credentials'], _inputs['paths'], _send_conn,))
    # _stream_process.start()
    #
    # read_process(_inputs['paths']['price_history_path'], _receive_conn)
    # print('d')