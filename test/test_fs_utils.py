import os
from pathlib import Path
import glob

import pytest

from fdb_utils.fs_utils import is_directory_larger_than, get_directory_size
from test.conftest import data_dir

def test_is_directory_larger_than(mocker):

    mock_1MB_dir = '/dummy/path'
    mocker.patch('fdb_utils.fs_utils.get_directory_size', return_value=1000**2)

    assert is_directory_larger_than(mock_1MB_dir, '1KB') == True
    assert is_directory_larger_than(mock_1MB_dir, '1GB') == False

    mock_5TB_dir = '/dummy/path'
    mocker.patch('fdb_utils.fs_utils.get_directory_size', return_value=5*1000**4)

    assert is_directory_larger_than(mock_5TB_dir, '6TB') == False
    assert is_directory_larger_than(mock_5TB_dir, '3TB') == True



def test_get_directory_size(data_dir):
    # This test depends on only a single file being contained within directory.

    grib_files = [Path(file) for file in glob.glob(f"{data_dir}/*.grib")]

    expected = 0

    for grib_file in grib_files:
        expected += os.path.getsize(grib_file)

    result = get_directory_size(data_dir)
    assert expected == result

