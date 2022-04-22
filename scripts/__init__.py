import data_manager.utils
import src.floor_ceiling_regime
import regime

import json

if __name__ == '__main__':
    with open(r'..\data_args\scan_args.json', 'r') as args_fp:
        _args = json.load(args_fp)
    data_manager.utils.main(
        scan_args=_args,
        strategy_simulator=src.floor_ceiling_regime.fc_scale_strategy,
        expected_exceptions=(regime.NotEnoughDataError, src.floor_ceiling_regime.NoEntriesError)
    )
