import shutil
import string
from datetime import datetime
from pathlib import Path
from secrets import choice
from unittest.mock import patch

import eccodes
import pytest

def _generate_file_to_upload(
    base_path: Path, data_dir: Path, suffix="", random=False
) -> tuple[Path, str, str]:

    file_timestamp = datetime.now().strftime("%y%m%d") + "00"

    if not random:
        dst_folder = Path(base_path / f"{file_timestamp}_636/fxshare")
    else:
        random_str = "".join(choice(string.ascii_lowercase) for _ in range(10))
        dst_folder = Path(base_path / random_str)

    dst_folder.mkdir(parents=True, exist_ok=True)
    file_name = "_FXINP_lfrf00010000_003" + suffix
    file_to_upload = dst_folder / file_name

    shutil.copy(data_dir / "test.grib", file_to_upload)

    return file_to_upload, file_name, file_timestamp



LEVEL_TYPE_MAPPING = {
    "ml": "hybrid",
    "sfc": "surface",
    "pl": "isobaricInPa"
}

def _build_modification_string(
    date: str | None = None,
    time: str | None = None,
    step: int | str | None = None,
    number: int | None = None,
    levtype: str | None = None,
    level: float | None = None) -> str:
    modification = []

    if date is not None:
        modification.append(f"dataDate={date}")
    if time is not None:
        modification.append(f"dataTime={time}")
    if step is not None:
        modification.append(f"step={step}")
    if number is not None:
        modification.append(f"number={number}")
    if levtype is not None:
        modification.append(f"typeOfLevel={LEVEL_TYPE_MAPPING.get(levtype, '')}")
    if level is not None:
        modification.append(f"level={level}")

    return ",".join(modification)


def _process_grib_file(path: Path, modification: str) -> int:
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

    return cnt

def _verify_modifications(
    path: Path,
    date: str | None = None,
    time: str | None = None,
    step: int | str | None = None,
    number: int | None = None,
    level: float | None = None
    ):

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
        if level is not None:
            assert eccodes.codes_get(gid, "level", float) == float(level)
        eccodes.codes_release(gid)


def _modify_grib_file(
    path: Path,
    date: str | None = None,
    time: str | None = None,
    step: int | str | None = None,
    number: int | None = None,
    levtype: str | None = None,
    level: float | None = None
) -> None:
    """Modify keys in a GRIB file for testing."""

    modification = _build_modification_string(date, time, step, number, levtype, level)

    print("Modifying GRIB file: %s %s" % (path, modification))

    cnt = _process_grib_file(path, modification)

    _verify_modifications(path, date, time, step, number, level)

    shutil.move(str(path) + "_modified", str(path))

    print("Modified %s records in GRIB file: %s" % (cnt, path))
