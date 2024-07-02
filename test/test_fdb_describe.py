from datetime import datetime

import pytest

from fdb_utils.user.describe import list_all_values, get_archived_forecasts
from test.test_fdb_management import _generate_file_to_upload, _modify_grib_file
from test.conftest import fdb

def test_list_all_values(tmp_path, data_dir, fdb):

    # Generate GRIB files with different dates and archive to FDB
    file_to_upload_1, _, _ = _generate_file_to_upload(tmp_path, data_dir, random=True)
    file_to_upload_2, _, _ = _generate_file_to_upload(tmp_path, data_dir, random=True)
    file_to_upload_3, _, _ = _generate_file_to_upload(tmp_path, data_dir, random=True)
    file_to_upload_4, _, _ = _generate_file_to_upload(tmp_path, data_dir, random=True)

    _modify_grib_file(file_to_upload_1, date='20240202', time='300', number=5, step=0)
    _modify_grib_file(file_to_upload_2, date='20240202', time='300', number=5, step=1)
    _modify_grib_file(file_to_upload_3, date='20240203', time='300', number=1, step=2)
    _modify_grib_file(file_to_upload_4, date='20240203', time='600', number=2, step=3)

    for file in (file_to_upload_1, file_to_upload_2, file_to_upload_3, file_to_upload_4):
        with open(file, "rb") as f:
            fdb.archive(f.read())

    fdb.flush()

    assert list_all_values('time')['time'] == {'0300', '0600'}
    assert list_all_values('step')['step'] == {'0','1','2','3'}
    assert list_all_values('step', date='20240202')['step'] == {'0','1'}
    assert list_all_values('number', date='20240202')['number'] == {5}


def test_get_archived_forecasts(data_dir, tmp_path, fdb):


    #generate some files with different dates and archive to FDB
    file_to_upload_1, _, _ = _generate_file_to_upload(tmp_path, data_dir, random=True)
    file_to_upload_2, _, _ = _generate_file_to_upload(tmp_path, data_dir, random=True)
    file_to_upload_3, _, _ = _generate_file_to_upload(tmp_path, data_dir, random=True)

    _modify_grib_file(file_to_upload_1, date='20240202', time='300')
    _modify_grib_file(file_to_upload_2, date='20240202', time='600')
    _modify_grib_file(file_to_upload_3, date='20240302', time='900')

    with open(file_to_upload_1, "rb") as f:
        fdb.archive(f.read())
    with open(file_to_upload_2, "rb") as f:
        fdb.archive(f.read())

    fdb.flush()

    result = get_archived_forecasts( {'levtype': 'sfc'} )

    assert result == [datetime(2024, 2, 2, 3), datetime(2024, 2, 2, 6)]

    with open(file_to_upload_3, "rb") as f:
        fdb.archive(f.read())
    fdb.flush()

    result = get_archived_forecasts( {'levtype': 'sfc'} )

    assert result == [datetime(2024, 2, 2, 3), datetime(2024, 2, 2, 6), datetime(2024, 3, 2, 9)]