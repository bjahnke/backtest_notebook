import cbpro_access
import json

import pandas as pd

if __name__ == '__main__':
    with open(r'..\credentials\cbpro.json', 'r') as cred_file:
        cb_creds = json.load(cred_file)
    client = cbpro_access.CbproClient(**cb_creds)
    res = client.download_price_data(interval=1, interval_type='d', back_shift=0, num_bars=600)
    print('d')


