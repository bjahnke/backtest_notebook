import multiprocessing as mp
import json

import numpy as np
import tda_access.access as taa
from time import perf_counter
import pandas as pd


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


def get_transition_table(transition_info):
    data_table = pd.DataFrame.from_dict(transition_info)
    fees_table = pd.DataFrame(list(data_table['fees']))
    transaction_table = pd.DataFrame(list(data_table['transactionItem']))

    instrument_table = transaction_table.instrument.dropna()
    instrument_table = pd.DataFrame(
        list(instrument_table), index=instrument_table.index
    )

    trade_id = 'tx_id'

    instrument_table = (
        instrument_table
        .reset_index()
        .rename(columns={'index': trade_id})
    )

    trade_instrument_relation = instrument_table[[trade_id, 'symbol']]
    instrument_table = instrument_table.drop(columns=[trade_id])
    instrument_table = instrument_table.drop_duplicates(subset=['symbol'])

    transaction_table = (
        transaction_table
        .drop(columns=['instrument'])
        .reset_index()
        .rename(columns={'index': trade_id})
    )
    data_table = data_table.drop(columns=['fees', 'transactionItem'])

    return (
        data_table,
        fees_table,
        transaction_table,
        instrument_table,
        trade_instrument_relation
    )


def merge_new_data(new_tables, cached_tables):
    for i, fetched_table in enumerate(new_tables):
        cached_table = cached_tables[i]
        new_data = fetched_table.loc[fetched_table.transaction_id != cached_table.transaction_id]


if __name__ == '__main__':
    with open('..\\data_args\\credentials.json', 'r') as cred_file:
        _inputs = json.load(cred_file)

    td_client = taa.TdBrokerClient(_inputs['credentials'])
    _account_info = td_client.account_info().json()
    with open('..\\data_args\\account_info.json', 'w') as fp:
        json.dump(_account_info, fp, indent=2)

    # get/update position table
    _pos = get_position_table(_account_info)
    _pos.to_csv('..\\data\\position_data.csv')

    # get transaction history
    _tx_info = td_client.get_transactions().json()
    _tx_table = get_transition_table(_tx_info)
    _tx_table.to_csv('..\\data\\transaction_data.csv')
    print('d')

    # TODO generate closing orders for existing positions

    # _receive_conn, _send_conn = mp.Pipe(duplex=True)
    # _stream_process = mp.Process(target=stream_app, args=(_inputs['credentials'], _inputs['paths'], _send_conn,))
    # _stream_process.start()
    #
    # read_process(_inputs['paths']['price_history_path'], _receive_conn)
    # print('d')

