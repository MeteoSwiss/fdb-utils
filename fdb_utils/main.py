import logging
from typing import Annotated
import sys

import typer

from fdb_utils.user.describe import list_all_values
from fdb_utils.fdb_utils import validate_environment

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

_logger = logging.getLogger(__name__)

app = typer.Typer(no_args_is_help=True)

validate_environment()

@app.command(no_args_is_help=True)
def list(
    show: Annotated[str, typer.Option(help='The keys to print, eg. "step,number,param"')],
    filter: Annotated[str, typer.Option(help='The metadata to filter results by, eg "date=20240624,time=0600".')]
    ) -> None:
    """List metadata of data archived of FDB.
    """


    show_keys = show.split(',')

    filter_key_value_pairs = filter.split(',')
    filter_by_values = dict(pair.split('=') for pair in filter_key_value_pairs)

    list_all_values(show_keys, filter_by_values)
