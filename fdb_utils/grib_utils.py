"""This module provides a function for reading GRIB files."""

import logging
from pathlib import Path

import eccodes

_logger = logging.getLogger(__name__)


def extract_metadata_from_grib_file(path: Path) -> dict:
    with open(path, "rb") as f:
        gid = eccodes.codes_grib_new_from_file(f)
        if gid is None:
            msg = f"Could not read grib file {path}."
            _logger.exception(msg)
            raise RuntimeError(msg)

        fcst_date = eccodes.codes_get_string(gid, 'mars.date')
        fcst_time = eccodes.codes_get_string(gid, 'mars.time')
        step = eccodes.codes_get_string(gid, 'mars.step')
        number = eccodes.codes_get_string(gid, 'mars.number')

        eccodes.codes_release(gid)

    return {
        'date': fcst_date,
        'time': fcst_time,
        'step': int(step),
        'number': int(number),
    }
