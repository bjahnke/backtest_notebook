import tda_access.access as taa
import pandas as pd
from time import perf_counter


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