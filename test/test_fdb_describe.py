from datetime import datetime

import pytest

from fdb_utils.user.describe import list_all_values, get_archived_forecasts,SCHEMA_KEYS
from test.utils import _generate_file_to_upload, _modify_grib_file
from test.conftest import fdb

def test_list_all_values(tmp_path, data_dir, fdb):

    # Generate GRIB files with different dates and archive to FDB

    files = []

    for _ in range(4):
        file, _, _ = _generate_file_to_upload(tmp_path, data_dir, random=True)
        files.append(file)

    _modify_grib_file(files[0], date='20240202', time='300', number=5, step=0)
    _modify_grib_file(files[1], date='20240202', time='300', number=5, step=1)
    _modify_grib_file(files[2], date='20240203', time='300', number=1, step=2)
    _modify_grib_file(files[3], date='20240203', time='600', number=2, step=3)

    for file in files:
        with open(file, "rb") as f:
            fdb.archive(f.read())

    fdb.flush()

    assert list_all_values('time')['time'] == {'0300', '0600'}
    assert list_all_values('step')['step'] == {'0','1','2','3'}
    assert list_all_values('step', date='20240202')['step'] == {'0','1'}
    assert list_all_values('number', date='20240202')['number'] == {5}
    assert list_all_values(date='20240203')['step'] == {'2','3'}
    assert list_all_values(date='20240203')['number'] == {1,2}

def test_listall_values_filtered(tmp_path, data_dir, fdb):

    # Generate GRIB files with different dates and archive to FDB
    files = []

    for _ in range(4):
        file, _, _ = _generate_file_to_upload(tmp_path, data_dir, random=True)
        files.append(file)

    _modify_grib_file(files[0], date='20240201', time='300', number=4, step=1)
    _modify_grib_file(files[1], date='20240201', time='600', number=4, step=2)
    _modify_grib_file(files[2], date='20240203', time='900', number=1, step=3)
    _modify_grib_file(files[3], date='20240203', time='1200', number=2, step=4)

    for file in files:
        with open(file, "rb") as f:
            fdb.archive(f.read())

    fdb.flush()

    assert list_all_values('time')['time'] == {'0300', '0600', '0900', '1200'}
    assert list_all_values('step')['step'] == {'1','2','3', '4'}
    assert list_all_values('step', date='20240201')['step'] == {'1','2'}
    assert list_all_values('number', date='20240201')['number'] == {4}


def test_get_archived_forecasts(data_dir, tmp_path, fdb):


    #generate some files with different dates and archive to FDB
    files = []

    for _ in range(3):
        file, _, _ = _generate_file_to_upload(tmp_path, data_dir, random=True)
        files.append(file)

    _modify_grib_file(files[0], date='20240202', time='300')
    _modify_grib_file(files[1], date='20240202', time='600')
    _modify_grib_file(files[2], date='20240302', time='900')

    for file in files[:2]:
        with open(file, "rb") as f:
            fdb.archive(f.read())

    fdb.flush()

    result = get_archived_forecasts( {'levtype': 'sfc'} )

    assert result == [datetime(2024, 2, 2, 3), datetime(2024, 2, 2, 6)]

    with open(files[2], "rb") as f:
        fdb.archive(f.read())
    fdb.flush()

    result = get_archived_forecasts( {'levtype': 'sfc'} )

    assert result == [datetime(2024, 2, 2, 3), datetime(2024, 2, 2, 6), datetime(2024, 3, 2, 9)]


def test_validate_filter_error(tmp_path, data_dir, fdb):

    file_to_upload_1, _, _ = _generate_file_to_upload(tmp_path, data_dir, random=True)

    _modify_grib_file(file_to_upload_1, date='20240202', time='300')

    with open(file_to_upload_1, "rb") as f:
        fdb.archive(f.read())

    fdb.flush()

    with pytest.raises(RuntimeError, match=f"Key datetime must be one of '{', '.join(SCHEMA_KEYS)}'"):
        list_all_values(datetime='202402020300')

def test_get_archived_forecast_empty_request(tmp_path, data_dir, fdb):

    file_to_upload_1, _, _ = _generate_file_to_upload(tmp_path, data_dir, random=True)
    file_to_upload_2, _, _ = _generate_file_to_upload(tmp_path, data_dir, random=True)

    _modify_grib_file(file_to_upload_1, date='20240202', time='300',step=0, number=1, levtype='sfc')
    _modify_grib_file(file_to_upload_2, date='20240203', time='300',step=1, number=0, levtype='sfc')

    for file in (file_to_upload_1, file_to_upload_2):
        with open(file, "rb") as f:
            fdb.archive(f.read())

    fdb.flush()

    result = get_archived_forecasts()
    print(result)

    assert result == [datetime(2024, 2, 2, 3, 0)]

def test_list_all_values_levelist_sorting(tmp_path, data_dir, fdb):

    files = []

    for _ in range(3):
        file, _, _ = _generate_file_to_upload(tmp_path, data_dir, random=True, levelist=True)
        files.append(file)

    _modify_grib_file(files[0], date='20240202', time='300', level=float(1), step=3)
    _modify_grib_file(files[1], date='20240203', time='600', level=float(3), step=3)
    _modify_grib_file(files[2], date='20240203', time='900', level=float(2), step=3)

    for file in files:
        with open(file, "rb") as f:
            fdb.archive(f.read())

    fdb.flush()

    assert list_all_values('levelist')['levelist'] == {1.0, 2.0, 3.0}
    assert list_all_values(date='20240203')['levelist'] == {2.0, 3.0}
