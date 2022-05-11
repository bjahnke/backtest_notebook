import data_manager.utils
import data_manager.scanner as scanner
import src.floor_ceiling_regime
import regime
import yfinance
import pandas as pd
import json
import pickle
import data_manager.utils as sbtu


def load_data_package():
    _data_loader = sbtu.DataLoader.init_from_paths(r'..\data_args\other.json', r'..\data_args\base.json')
    _strategy_path = _data_loader.file_path('strategy_lookup.pkl')
    with open(_strategy_path, 'rb') as f:
        _strategy_lookup = pickle.load(f)

    _entry_path = _data_loader.file_path('entry_table.pkl')
    with open(_entry_path, 'rb') as f:
        _entry_table = pickle.load(f)

    _peak_path = _data_loader.file_path('peak_table.pkl')
    with open(_peak_path, 'rb') as f:
        _peak_table = pickle.load(f)

    _bench_str = 'SPY'
    _interval = '15m'
    _price_data = pd.read_csv(_data_loader.history_path(), index_col=0, header=[0, 1]).astype('float64')
    _bench = pd.read_csv(_data_loader.bench_path(), index_col=0).astype('float64')
    _strategy_overview = pd.read_csv(_data_loader.file_path('stat_overview.csv'))
    return (
        _price_data,
        _bench,
        _strategy_overview,
        _peak_table,
        _entry_table,
        _strategy_lookup
    )


def load_cbpro_data(other_path, base_path):
    data_loader = data_manager.utils.DataLoader.init_from_paths(other_path, base_path)
    price_data = pd.read_csv(data_loader.history_path(), index_col=0, header=[0, 1])
    price_data = price_data.ffill()
    ticks = list(price_data.columns.levels[0].unique())
    return ticks, data_manager.utils.PriceGlob(price_data), None, None, data_loader


if __name__ == '__main__':
    with open(r'..\data_args\scan_args.json', 'r') as args_fp:
        _args = json.load(args_fp)
    load_data = _args['load_data']

    _scan_data = data_manager.utils.load_scan_data(**load_data)

    data_manager.utils.main(
        scan_args=_args,
        strategy_simulator=src.floor_ceiling_regime.fc_scale_strategy,
        expected_exceptions=(regime.NotEnoughDataError, src.floor_ceiling_regime.NoEntriesError),
        # scan_data=data_manager.utils.load_scan_data(load_data['other_path'], load_data['base_path'],)
        scan_data=_scan_data
    )
