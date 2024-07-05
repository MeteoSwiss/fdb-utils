"""This module provides a function for archiving files to FDB."""

import logging
import os
import subprocess
from pathlib import Path
from datetime import datetime


_logger = logging.getLogger(__name__)


def wipe_fdb(forecasts: list[datetime], exception: int = 0) -> None:
    """
    Delete oldest forecast stored in FDB.
    To ignore statically archived data (the oldest forecast), set exception = 1 else 0
    """

    if not forecasts:
        raise RuntimeError(f'Unable to wipe a forecast from empty list: {forecasts}')

    if exception > len(forecasts) - 1:
        raise ValueError(
            f'Cannot ignore index {exception} of {len(forecasts)} archived forecasts.')

    forecasts.sort()

    to_delete_date=forecasts[exception].strftime("%Y%m%d")
    to_delete_time=forecasts[exception].strftime("%H%M")
    wipe_filter=f"date={to_delete_date},time={to_delete_time}"

    # FDB wipe is not available in the Python API so use the CLI.
    fdb_wipe_exe = f"{os.environ['FDB5_HOME']}/bin/fdb-wipe"

    if not Path(fdb_wipe_exe).exists():
        raise RuntimeError(f"fdb wipe executable does not exist: {fdb_wipe_exe}")

    _logger.info("Deleting forecast: %s", wipe_filter)

    # The --unsafe-wipe-all flag also wipes all (unowned) contents of an unclean database.
    subprocess.run([fdb_wipe_exe, "--doit", "--unsafe-wipe-all", "--minimum-keys=", wipe_filter], check=True)
