import cbpro_access
import json
import pandas as pd
import data_manager.utils as dmu
import data_manager.scanner as scanner


def download_macro():
    interval = 1
    interval_type = 'h'
    base_address = fr'C:\Users\bjahnke\OneDrive - bjahnke\OneDrive\algo_data\history\cbpro_{interval}{interval_type}'
    num_bars = 600

    interval_str = f'{interval}{interval_type}'

    with open(r'..\credentials\cbpro.json', 'r') as cred_file:
        cb_creds = json.load(cred_file)
    client = cbpro_access.CbproClient(**cb_creds)

    res = client.download_price_data(
        interval=interval, interval_type=interval_type, back_shift=0, num_bars=num_bars,
    )
    dates = res.index
    res = res.reset_index(drop=True)
    time_series = pd.DataFrame({'time': dates}, index=res.index)
    # bench_data = scanner.yf_get_stock_data('BITW', days=num_bars, interval=interval_str)
    # bench_data = bench_data.reset_index()
    # bench_time_series = pd.DataFrame({'time': bench_data.time}, index=bench_data.index)

    res.to_csv(fr'{base_address}\history.csv')
    time_series.to_csv(fr'{base_address}\date_time.csv')
    # bench_data.to_csv(fr'{base_address}\bench.csv')
    # bench_time_series.to_csv(fr'{base_address}\bench.csv')

    print('d')


if __name__ == '__main__':
    download_macro()
    print('d')
