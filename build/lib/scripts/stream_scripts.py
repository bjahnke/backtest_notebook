import abstract_broker
import pandas as pd
from time import perf_counter
import typing as t


def setup(
        client: abstract_broker.AbstractBrokerClient,
        stream_settings: t.Dict,
        symbols: t.List[str],
        send_conn,
):
    stream = client.init_stream(
        live_quote_fp=stream_settings['live_quote_path'],
        price_history_fp=stream_settings['price_history_path'],
        **stream_settings['default_price_query'],
    )
    stream.run_stream(send_conn, symbols=symbols)


def read_process(price_history_path: str, writer_receive_conn: mp.Pipe):
    """
    Pole pipe until we receive a signal that there is new data.

    :param price_history_path:
    :param writer_receive_conn:
    :return:
    """
    data = pd.DataFrame()

    while True:
        if writer_receive_conn.poll():
            recv_start = perf_counter()
            _ = writer_receive_conn.recv()
            new_data = pd.read_csv(price_history_path)
            read_time = perf_counter() - recv_start
            recv_start = perf_counter()
            if new_data.equals(data):
                continue
            else:
                data = new_data
                equals_check = perf_counter() - recv_start
                print(f'read time: {read_time}')
                print(f'equals check: {equals_check}')

                yield data
