import datetime as dt

import matplotlib.pyplot as plt
import pytest
from unittest.mock import patch

import fdb_utils.ci.check_archive_status as cas


def test_overall_status_missing():
    status_dict = {
        "p1": [[0, 0, 0, 0], [0, 0, 0, 0]],
        "p2": [[0], [0], [0], [0]],
    }
    assert cas.overall_status(status_dict) == cas.ForecastStatus.MISSING


def test_overall_status_complete():
    status_dict = {
        "p1": [[1, 1, 1, 1], [1, 1, 1, 1]],
        "p2": [[1], [1], [1], [1]],
    }
    assert cas.overall_status(status_dict) == cas.ForecastStatus.COMPLETE


def test_overall_status_incomplete():
    status_dict = {
        "p1": [[1, 1, 1, 0], [1, 1, 1, 1]],
        "p2": [[1], [1], [1], [1]],
    }
    assert cas.overall_status(status_dict) == cas.ForecastStatus.INCOMPLETE


def test_fx_filename():
    assert cas.fx_filename("suf", 0, 0) == "_FXINP_lfrf0000000_000suf"
    assert cas.fx_filename("", 1, 10) == "_FXINP_lfrf0010000_001"
    assert cas.fx_filename("s", 123, 49) == "_FXINP_lfrf0201000_123s"


def test_get_failed_files():
    success_dict = {
        "suf1": [[1, 1, 0], [0, 1, 1]],
        "suf2": [[0, 1, 1], [1, 1, 1], [1, 0, 1]],
    }
    expected_files = [
        "_FXINP_lfrf0002000_000suf1",
        "_FXINP_lfrf0000000_001suf1",
        "_FXINP_lfrf0000000_000suf2",
        "_FXINP_lfrf0001000_002suf2",
    ]
    assert cas.get_failed_files(success_dict) == expected_files


def test_last_run_time_ch1():
    icon_1 = cas.COLLECTIONS["icon-ch1-eps"]

    # Verify that ICON-CH1 run times are every three hours.
    first_time_ch1 = dt.datetime.fromisoformat("2025-01-01T02:45Z")
    first_run_time = dt.datetime.fromisoformat("2025-01-01T00:00Z")
    assert cas.last_run_time(icon_1, first_time_ch1) == first_run_time
    assert (
        cas.last_run_time(icon_1, first_time_ch1 + dt.timedelta(hours=1))
        == first_run_time
    )
    assert (
        cas.last_run_time(icon_1, first_time_ch1 + dt.timedelta(hours=2))
        == first_run_time
    )
    assert cas.last_run_time(
        icon_1, first_time_ch1 + dt.timedelta(hours=3)
    ) == first_run_time + dt.timedelta(hours=3)
    assert cas.last_run_time(
        icon_1, first_time_ch1 + dt.timedelta(hours=6)
    ) == first_run_time + dt.timedelta(hours=6)
    assert cas.last_run_time(
        icon_1, first_time_ch1 + dt.timedelta(hours=7)
    ) == first_run_time + dt.timedelta(hours=6)


def test_last_run_time_ch2():
    icon_2 = cas.COLLECTIONS["icon-ch2-eps"]

    # Verify that ICON-CH2 run times are every six hours.
    first_time_ch2 = dt.datetime.fromisoformat("2025-01-01T03:45Z")
    first_run_time = dt.datetime.fromisoformat("2025-01-01T00:00Z")
    assert cas.last_run_time(icon_2, first_time_ch2) == first_run_time
    assert (
        cas.last_run_time(icon_2, first_time_ch2 + dt.timedelta(hours=1))
        == first_run_time
    )
    assert (
        cas.last_run_time(icon_2, first_time_ch2 + dt.timedelta(hours=3))
        == first_run_time
    )
    assert (
        cas.last_run_time(icon_2, first_time_ch2 + dt.timedelta(hours=5))
        == first_run_time
    )
    assert cas.last_run_time(
        icon_2, first_time_ch2 + dt.timedelta(hours=6)
    ) == first_run_time + dt.timedelta(hours=6)
    assert cas.last_run_time(
        icon_2, first_time_ch2 + dt.timedelta(hours=7)
    ) == first_run_time + dt.timedelta(hours=6)


def test_last_run_time_lead_time():
    icon_1 = cas.COLLECTIONS["icon-ch1-eps"]

    # Verify that the lead time is taken into account.
    first_time_lead_time = dt.datetime.fromisoformat("2025-01-01T03:30Z")
    first_run_time = dt.datetime.fromisoformat("2025-01-01T00:00Z")
    assert cas.last_run_time(icon_1, first_time_lead_time) == first_run_time


def test_create_figure():
    fig, axs = cas.create_figure(cas.COLLECTIONS["icon-ch1-eps"])
    assert fig is not None
    assert len(axs) == 4


def test_plot_status():
    status = [[1, 1, 1], [1, 1, 1], [1, 1, 0], [1, 0, 1]]
    _, ax = plt.subplots()
    cas.plot_status(ax, status, "suf")
    assert "suf" in ax.get_title("left")
    assert ax.get_xlabel() == "step"
    assert [x.get_text() for x in ax.get_xticklabels()] == ["0", "1", "2"]
    assert ax.get_ylabel() == "member"
    assert [y.get_text() for y in ax.get_yticklabels()] == ["0", "1", "2", "3"]


def test_plot_history():
    status = [
        cas.ForecastStatus.COMPLETE,
        cas.ForecastStatus.INCOMPLETE,
        cas.ForecastStatus.MISSING,
    ]
    labels = ["2501010900", "2501010600", "2501010300"]
    _, ax = plt.subplots()
    cas.plot_history(ax, status, labels)
    assert "Historical" in ax.get_title("left")
    assert "date" in ax.get_xlabel()
    assert [x.get_text() for x in ax.get_xticklabels()] == labels
    assert len(ax.get_yticks()) == 0


def return_steps(missing_values: dict[str, dict[str, list[int]]]):
    def list_all_values_mock(*filter_keys: str, **filter_by_values: str):
        param = filter_by_values["param"]
        number = filter_by_values["number"]
        model = filter_by_values["model"]

        num_steps = 1 if param == "500004" else cas.COLLECTIONS[model].steps
        missing_steps = missing_values[param].get(number, [])
        steps = []
        for s in range(num_steps):
            if s not in missing_steps:
                steps.append(str(s))
        return {"step": steps}

    return list_all_values_mock


# mock out list_all_values
@patch("fdb_utils.ci.check_archive_status.list_all_values")
def test_get_archive_status(list_values, tmp_path, data_dir):
    missing_values = {
        "500004": {"0": [0], "1": [0]},
        "500006": {"0": [30, 31], "9": [0, 1]},
        "500001": {"1": [0], "2": [10]},
    }
    list_values.side_effect = return_steps(missing_values)

    forecast_time = dt.datetime.fromisoformat("2025-02-02T03:00Z")
    archive_status = cas.get_archive_status("icon-ch1-eps", forecast_time)

    assert "c" in archive_status.keys()
    assert "p" in archive_status.keys()
    assert "" in archive_status.keys()
    assert archive_status["c"][0][0] == 0
    assert archive_status["c"][1][0] == 0
    assert archive_status["p"][0][30] == 0
    assert archive_status["p"][0][31] == 0
    assert archive_status["p"][9][0] == 0
    assert archive_status["p"][9][1] == 0
    assert archive_status[""][1][0] == 0
    assert archive_status[""][2][10] == 0
    # No other files are missing.
    status_sum = 0
    for param_status in archive_status.values():
        status_sum += sum(sum(row) for row in param_status)
    assert status_sum == 11 + (11 * 33) + (11 * 33) - 8
