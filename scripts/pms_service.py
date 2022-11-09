import stream_scripts
import tda_access.access as taa
import env
import pandas as pd
import multiprocessing as mp


def td_main(credentials, local_positions_path, stream_settings):
    td_client = taa.TdBrokerClient(credentials)
    _receive_conn, _send_conn = mp.Pipe(duplex=True)
    # where do symbols come from?
    position_data = pd.read_excel(local_positions_path, sheet_name=None, index_col=0)
    symbols = list(position_data['Position'].symbol)
    stream = td_client.init_stream(
        live_quote_fp=stream_settings['live_quote_path'],
        price_history_fp=stream_settings['price_history_path'],
        **stream_settings['default_price_query'],
    )
    res = stream.run_stream(_send_conn, symbols)
    stream_process = mp.Process(
        target=res,
        # args=()
    )
    stream_process.start()
    stream_scripts.read_process(stream_settings['price_history_path'], _receive_conn)


if __name__ == '__main__':
    td_main(env.td_credentials, env.local_position_path, env.stream_settings)
