import pytest

from fdb_utils.ci.check_archive_status import (
    overall_status,
    fx_filename,
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
