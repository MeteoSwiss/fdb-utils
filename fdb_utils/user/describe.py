"""This module provides a function for descriing data within FDB."""

import logging
from datetime import datetime
from typing import Tuple

_logger = logging.getLogger(__name__)

SCHEMA_KEYS = ('date','expver','model','number','stream','time','type','levtype','param','step','levelist','class')

def _validate_filter(filter_by_values: dict) -> None:
    for k, _ in filter_by_values.items():
        if k not in SCHEMA_KEYS:
            raise RuntimeError(f"Key {k} must be one of '{', '.join(SCHEMA_KEYS)}'")

def _add_key_value(key_name: Tuple[str,...], key_value, res: dict) -> dict:
    if key_name not in ('number', 'levelist'):
        res[key_name].add(key_value)
    elif key_value is None:
        return res
    elif key_name == 'number' and key_value:
        res[key_name].add(int(key_value))
    elif key_name == 'levelist' and key_value:
        res[key_name].add(float(key_value))

    return res

def _print_result(flt_keys: str, output: dict) -> None:
    for requested_key in flt_keys:
        if requested_key not in output:
            print(f'{requested_key}: Key not found')

    if not output:
        print('No metadata found matching your request.')

    for key, value in output.items():
        if not value:
            continue

        if key == 'levelist':
            value = sorted(value, key=float)
        else:
            print(f'{key}: {value}')

    print('')


def list_all_values(*filter_keys: str, **filter_by_values: str) -> dict[str, set[str | int]]:
    """
    Print and return values from FDB, filtered by specified keys and values.

    This function retrieves key-value pairs from FDB using the `pyfdb` library,
    optionally filtered by specific keys and values. It prints the keys and their corresponding
    values from the database and returns a dictionary with the results.
    If no keys or values match the filters, 'None' is printed and an empty dictionary is returned.

    Parameters:
    -----------
    filter_keys : str
        Argument list of schema dimensions to filter the results by.
        If no keys are provided, all keys are included.
    filter_by_values : str
        Keyword arguments specifying key-value pairs to filter the results.
        If no filter values are provided, all entries are included.

    Returns:
    --------
    dict
        A dictionary where the keys are the dimensions and the
        values are sets containing the corresponding values from FDB.

    Example:
    --------
    >>> list_all_values('step', 'param', date='20240202', time='0600')

    """

    import pyfdb

    filter_values_msg = f" for {filter_by_values}" if filter_by_values else ''

    if filter_keys:
        print(f"Keys/Values of {', '.join(filter_keys)} in FDB{filter_values_msg}:")
    else:
        print(f"Keys/Values in FDB{filter_values_msg}:")

    if not filter_by_values:
        request = {}
    else:
        _validate_filter(filter_by_values)
        request = filter_by_values

    result: dict[str, set[str | int]] = {}

    for el in pyfdb.list(request, True, True):
        el_keys = el.get("keys", {})

        keys_to_process = filter_keys if filter_keys else el_keys.keys()

        for key in keys_to_process:
            result.setdefault(key, set())
            if key in el_keys:
                _add_key_value(key, el_keys[key], result)

    _print_result(filter_keys, output=result)
    return result



def get_archived_forecasts(request: dict | None = None) -> list[datetime]:
    """Check the forecast date and times which are currently archived in FDB."""

    import pyfdb

    # reduce the size of the request so that it takes less time.
    if not request:
        request = {
            'levtype': 'sfc',
            'step': '0',
            'number': '1'
        }

    datetime_keys = {
        f"{el['keys']['date']}:{el['keys']['time']}"
        for el in pyfdb.list(request, True, True)
    }

    fc_datetimes = []

    for datetime_key in datetime_keys:
        dt = datetime.strptime(datetime_key, "%Y%m%d:%H%M")
        fc_datetimes.append(dt)

    return sorted(fc_datetimes)
