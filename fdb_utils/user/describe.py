"""This module provides a function for descriing data within FDB."""

import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

SCHEMA_KEYS = ('date','expver','model','number','stream','time','type','levtype','param','step','levelist')

def _validate_filter(filter_by_values: dict) -> None:
    for k,v in filter_by_values.items():
        if k not in SCHEMA_KEYS:
            raise RuntimeError(f"Key {k} must be one of '{', '.join(SCHEMA_KEYS)}'")


def list_all_values(*filter_keys: str, **filter_by_values: str) -> dict[str, set[str | int]]:
    """
    Print and return values from FDB, filtered by specified keys and values.

    This function retrieves key-value pairs from FDB using the `pyfdb` library, optionally filtered by specific keys and values.
    It prints the keys and their corresponding values from the database and returns a dictionary with the results.
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
        A dictionary where the keys are the dimensions and the values are sets containing the corresponding values from FDB.

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
        if not filter_keys: 
            for key in el['keys']:
                if not key in result:
                    result[key] = set()
                result[key].add(el['keys'][key] if key not in ('number, levelist') else int(el['keys'][key]))
        else:
            for key in filter_keys:
                if not key in result:
                    result[key] = set()
                if key in el['keys']:
                    result[key].add(el['keys'][key] if key not in ('number, levelist') else int(el['keys'][key]))

    for requested_key in filter_keys:
        if not result[requested_key]:
            print(f'{requested_key}: Key not found')
            result.pop(requested_key)

    if not result:
        print('None')

    for key in result:
        if result[key]:
            print(f'{key}: {result[key]}')

    print('')
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
