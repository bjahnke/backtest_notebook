from __future__ import annotations
import json
import typing

import numpy as np
import tda_access.access as taa
from time import perf_counter
import pandas as pd
from dataclasses import dataclass, field


@dataclass
class TransactionTables:
    data: pd.DataFrame
    fees: pd.DataFrame
    transaction: pd.DataFrame
    position: pd.DataFrame
    path: str = field(init=False)

    @classmethod
    def read_excel(cls, path):
        obj = cls(**pd.read_excel(path, sheet_name=None, index_col=0))
        obj.path = path
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

    def to_excel(self, path):
        with pd.ExcelWriter(path, engine='xlsxwriter') as writer:
            self.data.to_excel(excel_writer=writer, sheet_name='data')
            self.fees.to_excel(excel_writer=writer, sheet_name='fees')
            self.transaction.to_excel(excel_writer=writer, sheet_name='transaction')
            self.position.to_excel(excel_writer=writer, sheet_name='positions')

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

        if not self.position.equals(positions):
            self.position = positions
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


def stream_app(credentials, paths, send_conn):
    _client = taa.TdBrokerClient(credentials=credentials)
    _stream = _client.init_stream(
        live_quote_fp=paths['live_quote_path'],
        price_history_fp=paths['price_history_path'],
        interval=1,
    )

    _stream.run_stream(send_conn, symbols=['AAPL', 'GOOGL', 'ABBV', 'AMZN', 'NFLX'])


def read_process(price_history_path, writer_receive_conn):
    data = pd.DataFrame()

    while True:
        if writer_receive_conn.poll():
            recv_start = perf_counter()
            _ = writer_receive_conn.recv()
            new_data = pd.read_csv(price_history_path)
            read_time = perf_counter() - recv_start
            if new_data.equals(data):
                continue
            else:
                data = new_data
                equals_check = perf_counter() - recv_start
                print(f'read time: {read_time}')
                print(f'equals check: {equals_check}')


"""
Json Structure
{ 
  "credentials": {
    "client": {
      "api_key": "",
      "redirect_uri": "https://localhost",
      "token_path": ""
    },
    "account_id": int
  },
  "paths": {
    "live_quote_path": "",
    "price_history_path": ""
  }
}
"""


def get_position_table(account_info):
    pos = pd.DataFrame.from_dict(account_info['securitiesAccount']['positions'])
    pos_id = pd.DataFrame(list(pos['instrument']))
    pos['quantity'] = pos['longQuantity'] - pos['shortQuantity']
    pos = pos.join(pos_id).drop(columns=['instrument'])
    return pos


def get_base_tx_table() -> typing.Tuple[pd.DataFrame, pd.DataFrame]:
    with open('..\\data_args\\credentials.json', 'r') as cred_file:
        _inputs = json.load(cred_file)

    td_client = taa.TdBrokerClient(_inputs['credentials'])
    _account_info = td_client.account_info().json()
    with open('..\\data_args\\account_info.json', 'w') as fp:
        json.dump(_account_info, fp, indent=2)

    # get/update position table
    _pos = get_position_table(_account_info)

    # get transaction history
    _tx_info = td_client.get_transactions().json()
    data_table = pd.DataFrame.from_dict(_tx_info)
    return data_table, _pos


def main_merge():
    local_path = '..\\data\\transaction_data_local.xlsx'
    tx_local = TransactionTables.read_excel(local_path)
    tx_base, positions = get_base_tx_table()
    nt = TransactionTables.parse_df(tx_base, positions)
    tx_local.update(tx_base, positions)
    tx_local.to_excel(local_path)


if __name__ == '__main__':
    # main_merge()
    # _tx_tables.to_excel('..\\data\\transaction_data_local.xlsx')
    local_path = '..\\data\\transaction_data_local.xlsx'
    tx_local = TransactionTables.read_excel(local_path)
    trades = tx_local.get_open_position_trades()
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

