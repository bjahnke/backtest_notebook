"""
loads configuration data to environment
"""
import json
import pathlib
import typing
import os
from dotenv import load_dotenv
import scripts.mytypes as mytypes
from sqlalchemy import create_engine


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

# Load environment variables from .env file
load_dotenv()

POSTGRES_USER = os.environ.get('POSTGRES_USER')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
POSTGRES_DB = os.environ.get('POSTGRES_DB')
DB_DRIVER_NAME = os.environ.get('DRIVER_NAME')
HOST = os.environ.get('HOST')
PORT = os.environ.get('PORT')
DATABASE = os.environ.get('DATABASE')
HISTORICAL_PRICES_DB = 'historical_prices'
NEON_DB = os.environ.get('NEON_DB_URL')

class HistoricalPrices:
    stock_data='stock_data'
    timestamp_data='timestamp_data'

class ConnectionEngines:
    class HistoricalPrices:
        NEON=create_engine(
            os.environ.get('NEON_DB_CONSTR')
        )

POSTGRES_CONNECTION_SETTINGS = mytypes.ConnectionSettings(
    drivername=DB_DRIVER_NAME,
    username=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=HOST,
    port=PORT,
    database=DATABASE
)

def get_connection_settings(
        database,
        drivername=DB_DRIVER_NAME,
        username=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=HOST,
        port=PORT,
) -> mytypes.ConnectionSettings:
    return mytypes.ConnectionSettings(
        drivername=drivername,
        username=username,
        password=password,
        host=host,
        port=port,
        database=database
    )