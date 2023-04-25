"""
loads configuration data to environment
"""
import json
import pathlib
import typing


def load_config(path: typing.Union[pathlib.Path, str]):
    with open(path) as fp:
        return json.load(fp)


_env_path = pathlib.Path('..') / 'data_args'

base = load_config(_env_path / 'base.json')
cbpro = load_config(_env_path / 'cbpro.json')
td_credentials = load_config(_env_path / 'credentials.json')['credentials']
other = load_config(_env_path / 'other.json')
scan_args = load_config(_env_path / 'scan_args.json')
stream_settings = scan_args['stream_settings']
local_position_path = scan_args['local_position_path']
data_manager_config = load_config(_env_path / 'data_manager_config.json')