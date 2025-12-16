import os
import shutil
import string
from datetime import datetime
from pathlib import Path
from secrets import choice
from test.conftest import data_dir, fdb, test_dir
from unittest.mock import patch

import eccodes
import pytest

from fdb_utils.management.wipe import wipe_fdb
from test.utils import _modify_grib_file

@pytest.fixture
def mock_fdb_wipe_exe(tmp_path, monkeypatch):
    fdb_wipe_exe = tmp_path / "bin" / "fdb-wipe"
    os.mkdir(tmp_path / "bin")
    fdb_wipe_exe.write_text("fake fdb-wipe executable content")
    monkeypatch.setenv("FDB5_DIR", str(tmp_path))
    return str(fdb_wipe_exe)


def test_wipe_fdb_empty_list():
    with pytest.raises(RuntimeError) as e:
        wipe_fdb([])

    assert "Unable to wipe a forecast from empty list" in str(e.value)

    with pytest.raises(ValueError) as e:
        wipe_fdb([datetime(2023, 1, 1), datetime(2023, 1, 2)], 3)

    assert "Cannot ignore index 3 of 2 archived forecasts" in str(e.value)


@patch("fdb_utils.management.wipe.subprocess.run")
def test_wipe_fdb(mock_subprocess_run, mock_fdb_wipe_exe):

    forecasts = [datetime(2023, 1, 1), datetime(2023, 1, 2)]

    wipe_fdb(forecasts)

    assert mock_subprocess_run.called_once_with(
        [mock_fdb_wipe_exe, "--doit", "--minimum-keys=", "date=20230101,time=0000"]
    )


@patch("fdb_utils.management.wipe.subprocess.run")
def test_wipe_fdb_model(mock_subprocess_run, mock_fdb_wipe_exe):

    forecasts = [datetime(2023, 1, 1), datetime(2023, 1, 2)]

    wipe_fdb(forecasts, model="icon-ch1-eps")

    assert mock_subprocess_run.called_once_with(
        [
            mock_fdb_wipe_exe,
            "--doit",
            "--minimum-keys=",
            "date=20230101,time=0000,model=icon-ch1-eps",
        ]
    )


def test_fdb_definitions(tmp_path: Path, data_dir: Path, fdb):

    total_records = 0
    archived_metadata = list()

    for filename in ("v_ml.grib", "v_pl.grib", "v_sfc.grib"):

        data_file_path = data_dir / filename
        file_path = tmp_path / filename
        shutil.copy(data_file_path, file_path)
        _modify_grib_file(file_path, date="20230410", step="4m")
        with open(file_path, "rb") as f:
            fdb.archive(f.read())

        metadata = _extract_metadata(file_path)
        archived_metadata += metadata
        total_records += len(metadata)
        print(f"metadata for {filename}", metadata)

    fdb.flush()

    print("Metadata archived according to eccodes")
    for item in archived_metadata:
        print(item)

    request = {
        "class": "od",
        "expver": "0001",
        "stream": "enfo",
        "date": "20230410",
        "step": "4m",
        "time": "0900",
    }

    keys_in_fdb: list[dict] = [item["keys"] for item in fdb.list(request, True, True)]

    reduced_keys_in_fdb = [
        {key: item.get(key, '') for key in archived_metadata[0].keys()} for item in keys_in_fdb
    ]

    print("Keys returned from FDB list")
    for key in reduced_keys_in_fdb:
        print(key)

    for expected in archived_metadata:
        assert expected in reduced_keys_in_fdb


def _extract_metadata(path: Path) -> list[dict]:

    file_metadata = []

    with open(path, "rb") as f:
        while (gid := eccodes.codes_grib_new_from_file(f)) is not None:

            record_metadata = {}
            fcst_date = eccodes.codes_get_string(gid, "mars.date")
            fcst_time = eccodes.codes_get_string(gid, "mars.time")
            step = eccodes.codes_get_string(gid, "mars.step")
            levtype = eccodes.codes_get_string(gid, "mars.levtype")
            mars_type = eccodes.codes_get_string(gid, "mars.type")
            if mars_type == "pf":
                number = eccodes.codes_get_string(gid, "mars.number")
            elif mars_type == "cf":
                number = ''
            else:
                number = None
                print(f"WARNING: unexpected type: {mars_type}")
            record_metadata["number"] = number
            record_metadata["levtype"] = levtype
            record_metadata["step"] = step
            record_metadata["time"] = fcst_time
            record_metadata["date"] = fcst_date

            file_metadata.append(record_metadata)

            eccodes.codes_release(gid)

    return file_metadata
