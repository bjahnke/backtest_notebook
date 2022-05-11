import data_manager.utils
import data_manager.scanner as scanner
import src.floor_ceiling_regime
import regime
import yfinance
import pandas as pd
import json


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

    data_manager.utils.main(
        scan_args=_args,
        strategy_simulator=src.floor_ceiling_regime.fc_scale_strategy,
        expected_exceptions=(regime.NotEnoughDataError, src.floor_ceiling_regime.NoEntriesError),
        scan_data=load_cbpro_data(load_data['other_path'], load_data['base_path'],)
    )
