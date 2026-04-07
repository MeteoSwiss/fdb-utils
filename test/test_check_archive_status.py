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
    assert cas.summary_status(status_dict) == cas.ForecastStatus.MISSING


def test_overall_status_complete():
    status_dict = {
        "p1": [[1, 1, 1, 1], [1, 1, 1, 1]],
        "p2": [[1], [1], [1], [1]],
    }
    assert cas.summary_status(status_dict) == cas.ForecastStatus.COMPLETE


def test_overall_status_incomplete():
    status_dict = {
        "p1": [[1, 1, 1, 0], [1, 1, 1, 1]],
        "p2": [[1], [1], [1], [1]],
    }
    assert cas.summary_status(status_dict) == cas.ForecastStatus.INCOMPLETE


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
    assert [y.get_text() for y in ax.get_yticklabels()] == ["ctrl", "1", "2", "3"]


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


def return_steps(missing_values: dict[tuple[str], dict[str, list[int]]]):
    """
    missing_values maps (param,date,time) -> { "ctrl": [...], "1": [...], "2": [...], ... }
    Control is addressed via type="cf"; perturbed via number="1..".
    """
    def list_all_values_mock(*filter_keys: str, **filter_by_values: str):
        model = filter_by_values["model"]
        param = filter_by_values["param"]
        num_steps = 1 if param == "500004" else cas.COLLECTIONS[model].steps

        date = filter_by_values["date"]
        time = filter_by_values["time"]

        if filter_by_values.get("type") == "cf":
            member_key = "ctrl"
        else:
            member_key = filter_by_values.get("number")  # "1","2",...

        missing_steps = missing_values.get((param, date, time), {}).get(member_key, [])
        steps = {str(s) for s in range(num_steps) if s not in missing_steps}
        return {"step": steps}

    return list_all_values_mock


@patch("fdb_utils.ci.check_archive_status.list_all_values")
def test_get_archive_status(list_values, tmp_path, data_dir):
    # Row 0 = control ("ctrl"); rows 1.. = numbers "1.."
    missing_values = {
        ("500004", "20250202", "0300"): {"ctrl": [0], "1": [0]},
        ("500006", "20250202", "0300"): {"ctrl": [30, 31], "9": [0, 1]},
        ("500001", "20250202", "0300"): {"1": [0], "2": [10]},
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


@patch("fdb_utils.ci.check_archive_status.list_all_values")
def test_historical_archive_status(list_values, tmp_path, data_dir):
    # helper to fill all members for ch1 (ctrl + 1..10)
    def all_members_map(step_list):
        d = {"ctrl": step_list}
        d.update({str(n): step_list for n in range(1, 11)})
        return d

    # Set one incomplete forecast and one missing forecast.
    missing_values = {
        ("500004", "20250202", "0000"): {"ctrl": [0]},  # latest-1 incomplete
        ("500004", "20250201", "2100"): all_members_map([0]),  # latest-2 missing
        ("500006", "20250201", "2100"): all_members_map(list(range(33))),
        ("500001", "20250201", "2100"): all_members_map(list(range(33))),
    }
    list_values.side_effect = return_steps(missing_values)

    first_forecast_time = dt.datetime.fromisoformat("2025-02-02T03:00Z")
    historical_summary, historical_dates = cas.historical_summary_status(
        first_forecast_time, cas.COLLECTIONS["icon-ch1-eps"]
    )

    assert historical_summary == [
        cas.ForecastStatus.INCOMPLETE,
        cas.ForecastStatus.MISSING,
        cas.ForecastStatus.COMPLETE,
        cas.ForecastStatus.COMPLETE,
        cas.ForecastStatus.COMPLETE,
        cas.ForecastStatus.COMPLETE,
        cas.ForecastStatus.COMPLETE,
    ]
    assert historical_dates == [
        "02/02/25 00",
        "01/02/25 21",
        "01/02/25 18",
        "01/02/25 15",
        "01/02/25 12",
        "01/02/25 09",
        "01/02/25 06",
    ]
