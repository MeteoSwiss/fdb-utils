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


@pytest.fixture
def mock_fdb_wipe_exe(tmp_path, monkeypatch):
    fdb_wipe_exe = tmp_path / "bin" / "fdb-wipe"
    os.mkdir(tmp_path / "bin")
    fdb_wipe_exe.write_text("fake fdb-wipe executable content")
    monkeypatch.setenv("FDB5_HOME", str(tmp_path))
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

        metadata = extract_metadata(file_path)
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

    keys_in_fdb = [item["keys"] for item in fdb.list(request, True, True)]

    reduced_keys_in_fdb = [
        {key: item[key] for key in archived_metadata[0].keys()} for item in keys_in_fdb
    ]

    print("Keys returned from FDB list")
    for key in reduced_keys_in_fdb:
        print(key)

    for expected in archived_metadata:
        assert expected in reduced_keys_in_fdb


def extract_metadata(path: Path) -> dict:

    file_metadata = []

    with open(path, "rb") as f:
        while (gid := eccodes.codes_grib_new_from_file(f)) is not None:
            fcst_date = eccodes.codes_get_string(gid, "mars.date")
            fcst_time = eccodes.codes_get_string(gid, "mars.time")
            step = eccodes.codes_get_string(gid, "mars.step")
            number = eccodes.codes_get_string(gid, "mars.number")
            levtype = eccodes.codes_get_string(gid, "mars.levtype")

            record_metadata = {
                "date": fcst_date,
                "time": fcst_time,
                "step": step,
                "number": number,
                "levtype": levtype,
            }

            file_metadata.append(record_metadata)

            eccodes.codes_release(gid)

    return file_metadata


def _generate_file_to_upload(
    base_path: Path, data_dir: Path, suffix="", random=False
) -> tuple[Path, str, str]:

    file_timestamp = datetime.now().strftime("%y%m%d") + "00"

    if not random:
        dst_folder = Path(base_path / f"{file_timestamp}_636/fxshare")
    else:
        random_str = "".join(choice(string.ascii_lowercase) for i in range(10))
        dst_folder = Path(base_path / random_str)

    dst_folder.mkdir(parents=True, exist_ok=True)
    file_name = "_FXINP_lfrf00010000_003" + suffix
    file_to_upload = dst_folder / file_name

    shutil.copy(data_dir / "test.grib", file_to_upload)

    return file_to_upload, file_name, file_timestamp


def _modify_grib_file(
    path: Path,
    date: str | None = None,
    time: str | None = None,
    step: int | str | None = None,
    number: int | None = None,
    levtype: str | None = None,
) -> None:
    # Modify keys in a GRIB file for testing.

    modification = ""

    if date is not None:
        modification += f"dataDate={date},"
    if time is not None:
        modification += f"dataTime={time},"
    if step is not None:
        modification += f"step={step},"
    if number is not None:
        modification += f"number={number},"
    if levtype is not None:
        if levtype == "ml":
            typeoflevel = "hybrid"
        if levtype == "sfc":
            typeoflevel = "surface"
        if levtype == "pl":
            typeoflevel = "isobaricInPa"
        modification += f"typeOfLevel={typeoflevel},"

    if modification.endswith(","):
        modification = modification[:-1]

    print("Modifying GRIB file: %s %s" % (path, modification))

    cnt = 0
    with open(path, "rb") as fi, open(str(path) + "_modified", "wb") as fo:
        while 1:
            cnt += 1
            gid = eccodes.codes_grib_new_from_file(fi)
            if gid is None:
                break

            eccodes.codes_set_key_vals(gid, modification)

            eccodes.codes_write(gid, fo)

            eccodes.codes_release(gid)

    with open(str(path) + "_modified", "rb") as f:
        gid = eccodes.codes_grib_new_from_file(f)
        if date is not None:
            assert eccodes.codes_get(gid, "dataDate", int) == int(date)
        if time is not None:
            assert eccodes.codes_get(gid, "dataTime", int) == int(time)
        if step is not None:
            assert eccodes.codes_get(gid, "step", str) == str(step)
        if number is not None:
            assert eccodes.codes_get(gid, "number", int) == int(number)
        eccodes.codes_release(gid)

    shutil.move(str(path) + "_modified", str(path))

    print("Modified %s records in GRIB file: %s" % (cnt, path))
