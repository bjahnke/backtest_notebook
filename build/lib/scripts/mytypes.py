from typing import Optional, Mapping, Sequence, Union
from pydantic import BaseModel


class DownloadParams(BaseModel):
    """
    parameters for downloading stock data
    """
    stock_table_url: str = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    bench: str = 'SPY'
    days: int = 365
    interval_str: str = '1d'

class ConnectionSettings(BaseModel):
    """
    A class representing the settings needed to establish a database connection.
    """

    # The name of the database driver to use (e.g. 'mysql', 'postgresql', 'sqlite').
    # This attribute is required.
    drivername: str

    # The username to use for authentication. This attribute is optional and defaults to `None`.
    username: Optional[str] = None

    # The password to use for authentication. This attribute is optional and defaults to `None`.
    password: Optional[str] = None

    # The hostname or IP address of the server to connect to. This attribute is optional and defaults to `None`.
    host: Optional[str] = None

    # The port number to connect to on the server. This attribute is optional and defaults to `None`.
    port: Optional[int] = None

    # The name of the database to connect to. This attribute is optional and defaults to `None`.
    database: Optional[str] = None

    # Additional options to pass to the database driver as a dictionary of string keys and string or list of strings values.
    # This attribute is optional and defaults to an empty dictionary.
    query: Mapping[str, Union[Sequence[str], str]] = {}
