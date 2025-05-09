import datetime as dt

import pytest

from fdb_utils.ci.check_archive_status import (
    overall_status,
    fx_filename,
    get_failed_files,
    last_run_time,
    COLLECTIONS,
    ForecastStatus,
)


def test_overall_status_missing():
    status_dict = {
        "p1": [[0, 0, 0, 0], [0, 0, 0, 0]],
        "p2": [[0], [0], [0], [0]],
    }
    assert overall_status(status_dict) == ForecastStatus.MISSING


def test_overall_status_complete():
    status_dict = {
        "p1": [[1, 1, 1, 1], [1, 1, 1, 1]],
        "p2": [[1], [1], [1], [1]],
    }
    assert overall_status(status_dict) == ForecastStatus.COMPLETE


def test_overall_status_incomplete():
    status_dict = {
        "p1": [[1, 1, 1, 0], [1, 1, 1, 1]],
        "p2": [[1], [1], [1], [1]],
    }
    assert overall_status(status_dict) == ForecastStatus.INCOMPLETE


def test_fx_filename():
    assert fx_filename("suf", 0, 0) == "_FXINP_lfrf0000000_000suf"
    assert fx_filename("", 1, 10) == "_FXINP_lfrf0010000_001"
    assert fx_filename("s", 123, 49) == "_FXINP_lfrf0201000_123s"


def test_get_failed_files():
    success_dict = {
        "suf1": [[1, 1, 0], [0, 1, 1]],
        "suf2": [[0, 1, 1],[1, 1, 1],[1, 0, 1]]
    }
    expected_files = ["_FXINP_lfrf0002000_000suf1", "_FXINP_lfrf0000000_001suf1",
                      "_FXINP_lfrf0000000_000suf2", "_FXINP_lfrf0001000_002suf2"]
    assert get_failed_files(success_dict) == expected_files


def test_last_run_time_ch1():
    icon_1 = COLLECTIONS["icon-ch1-eps"]

    # Verify that ICON-CH1 run times are every three hours.
    first_time_ch1 = dt.datetime.fromisoformat("2025-01-01T02:45Z")
    first_run_time = dt.datetime.fromisoformat("2025-01-01T00:00Z")
    assert last_run_time(icon_1, first_time_ch1) == first_run_time
    assert last_run_time(icon_1, first_time_ch1 + dt.timedelta(hours=1)) == first_run_time
    assert last_run_time(icon_1, first_time_ch1 + dt.timedelta(hours=2)) == first_run_time
    assert last_run_time(icon_1, first_time_ch1 + dt.timedelta(hours=3)) == first_run_time + dt.timedelta(hours=3)
    assert last_run_time(icon_1, first_time_ch1 + dt.timedelta(hours=6)) == first_run_time + dt.timedelta(hours=6)
    assert last_run_time(icon_1, first_time_ch1 + dt.timedelta(hours=7)) == first_run_time + dt.timedelta(hours=6)


def test_last_run_time_ch2():
    icon_2 = COLLECTIONS["icon-ch2-eps"]

    # Verify that ICON-CH2 run times are every six hours.
    first_time_ch2 = dt.datetime.fromisoformat("2025-01-01T03:45Z")
    first_run_time = dt.datetime.fromisoformat("2025-01-01T00:00Z")
    assert last_run_time(icon_2, first_time_ch2) == first_run_time
    assert last_run_time(icon_2, first_time_ch2 + dt.timedelta(hours=1)) == first_run_time
    assert last_run_time(icon_2, first_time_ch2 + dt.timedelta(hours=3)) == first_run_time
    assert last_run_time(icon_2, first_time_ch2 + dt.timedelta(hours=5)) == first_run_time
    assert last_run_time(icon_2, first_time_ch2 + dt.timedelta(hours=6)) == first_run_time + dt.timedelta(hours=6)
    assert last_run_time(icon_2, first_time_ch2 + dt.timedelta(hours=7)) == first_run_time + dt.timedelta(hours=6)


def test_last_run_time_lead_time():
    icon_1 = COLLECTIONS["icon-ch1-eps"]

    # Verify that the lead time is taken into account.
    first_time_lead_time = dt.datetime.fromisoformat("2025-01-01T03:30Z")
    first_run_time = dt.datetime.fromisoformat("2025-01-01T00:00Z")
    assert last_run_time(icon_1, first_time_lead_time) == first_run_time
