import logging
from typing import Annotated
import sys
import os

import typer

from fdb_utils.user.describe import list_all_values
from fdb_utils.fdb_utils import validate_environment, fdb_info

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

_logger = logging.getLogger(__name__)

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="fdb-utils CLI tool to help users and admins of FDB.")

validate_environment()

@app.command("list")
def list_metadata(
    show: Annotated[str, typer.Option(help='The keys to print, eg. "step,number,param"')] = "",
    filter_values: Annotated[str, typer.Option("--filter", help='The metadata to filter results by, eg "date=20240624,time=0600".')] = ""
    ) -> None:
    """List a union of metadata key/value pairs of GRIB messages archived to FDB."""

    if not filter_values:
        list_all = typer.confirm("Are you sure you want list everything in FDB? (may take some time).")
        if not list_all:
            raise typer.Abort()

    show_keys = show.split(',') if show else []

    filter_key_value_pairs = filter_values.split(',')
    filter_by_values = dict(pair.split('=') for pair in filter_key_value_pairs) if filter_values else {}

    os.environ['METKIT_RAW_PARAM']='1'

    list_all_values(*show_keys, **filter_by_values)


@app.command()
def info() -> None:
    """Print information on FDB environment."""
    fdb_info()
