import argparse
import datetime as dt
import logging
import sys
from dataclasses import dataclass
from enum import IntEnum

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

from fdb_utils.user.describe import list_all_values


@dataclass
class Collection:
    model: str
    members: int
    steps: int
    forecasts: int
    interval: dt.timedelta
    # How long after the start time of the run we expect the archive to be complete.
    delay: dt.timedelta


@dataclass
class Parameter:
    id: str
    file_suffix: str
    is_constant: bool
    field_filter: dict[str, str]


COLLECTIONS: dict[str, Collection] = {
    "icon-ch1-eps": Collection(
        model="icon-ch1-eps",
        members=11,
        steps=33,
        forecasts=8,
        interval=dt.timedelta(hours=3),
        delay=dt.timedelta(hours=2, minutes=30),
    ),
    "icon-ch2-eps": Collection(
        model="icon-ch2-eps",
        members=21,
        steps=121,
        forecasts=4,
        interval=dt.timedelta(hours=6),
        delay=dt.timedelta(hours=3, minutes=30),
    ),
}


# The poller archives the hourly rotlatlon grib files for constant params (suffix 'c'), single and multi level params
# (no suffix), and params on pressure levels (suffix 'p'). Each file contains data for all associated parameters for a
# single step and ensemble member. For further details on what each file type means, see:
# https://meteoswiss.atlassian.net/wiki/spaces/APN/pages/412975206/ICON-22+PP+Naming+scheme+for+intermediate+products#TC-tasks%2C-prepare-step
#
# An error during archival will result in all data for that file missing. Thus we can check that all steps and members
# are present for a single parameter that exists in the file to determine the status.
PARAMS: list[Parameter] = [
    Parameter(
        id="500004", file_suffix="c", is_constant=True, field_filter={"levtype": "sfc"}
    ),
    Parameter(
        id="500006",
        file_suffix="p",
        is_constant=False,
        field_filter={"levelist": "200", "levtype": "pl"},
    ),
    Parameter(
        id="500001",
        file_suffix="",
        is_constant=False,
        field_filter={"levelist": "1", "levtype": "ml"},
    ),
]


def last_run_time(collection: Collection, from_time: dt.datetime) -> dt.datetime:
    # Adjust the current timestamp by the expected time for forecast run + archival so that a run of the script at any
    # time is expected to succeed.
    adjusted_timestamp = (from_time - collection.delay).timestamp()
    run_interval = collection.interval.total_seconds()
    last_run_ts = adjusted_timestamp // run_interval * run_interval
    return dt.datetime.fromtimestamp(last_run_ts, tz=dt.timezone.utc)


def get_param_status(
    model: str, param: Parameter, date: str, time: str
) -> list[list[int]]:
    """Query FDB to determine the archival status for the parameter from the forecast at the provided time.

    Returns a 2d array with dimensions [member, step] containing 1 if the data is present and a 0 if not.
    """
    num_members = COLLECTIONS[model].members
    # Constant params are only defined on step 0, all others are defined for all steps.
    if param.is_constant:
        num_steps = 1
    else:
        num_steps = COLLECTIONS[model].steps
    filter_values = {"param": param.id, "model": model, "date": date, "time": time}

    status = []
    for member in range(num_members):
        param_filter = filter_values
        param_filter["number"] = str(member)
        param_filter |= param.field_filter
        steps_present = list_all_values(*["step"], **param_filter).get("step", [])
        steps_status = [1 if str(s) in steps_present else 0 for s in range(num_steps)]
        status.append(steps_status)

    return status


def get_archive_status(
    model: str, forecast_time: dt.datetime
) -> dict[str, list[list[int]]]:
    """Check if each file of the forecast has been archived."""
    date_str = forecast_time.strftime("%Y%m%d")
    time_str = forecast_time.strftime("%H00")

    archive_status = {}
    for p in PARAMS:
        param_status = get_param_status(model, p, date_str, time_str)
        archive_status[p.file_suffix] = param_status
    return archive_status


def fx_filename(suffix: str, member: int, step: int) -> str:
    """Construct the ICON fxshare filename for the provided parameters."""
    filename_template = "_FXINP_lfrf{dd:02}{hh:02}000_{mmm:03}"
    days = step // 24
    hours = step % 24
    filename = filename_template.format(dd=days, hh=hours, mmm=member) + suffix
    return filename


def get_failed_files(archive_status) -> list[str]:
    failed_files = []
    for file_suffix, param_status in archive_status.items():
        for member, steps_status in enumerate(param_status):
            for step, success in enumerate(steps_status):
                if not success:
                    failed_files.append(fx_filename(file_suffix, member, step))
    return failed_files


class ForecastStatus(IntEnum):
    MISSING = 0
    COMPLETE = 1
    INCOMPLETE = 2


def summary_status(status_dict: dict[list[list[int]]]) -> ForecastStatus:
    """Determine the archival status of the forecast as a whole."""
    any_success = False
    all_success = True
    for status in status_dict.values():
        any_success |= any(any(steps_stat) for steps_stat in status)
        all_success &= all(all(steps_stat) for steps_stat in status)

    if all_success:
        return ForecastStatus.COMPLETE
    if any_success:
        return ForecastStatus.INCOMPLETE
    return ForecastStatus.MISSING


def historical_summary_status(last_run_start: dt.datetime, collection: Collection):
    """Return the summary status for all past forecasts that should still exist."""
    history_status = []
    history_datetime = []
    past_start = last_run_start
    for _ in range(1, collection.forecasts):
        past_start = past_start - collection.interval
        past_status = get_archive_status(collection.model, past_start)
        history_status.append(summary_status(past_status))
        history_datetime.append(past_start.strftime("%y%m%d%H00"))
    return history_status, history_datetime


def plot_status(ax, status: list[list[int]], file_suffix: str):
    cmap = ListedColormap(["red", "green"])
    num_members = len(status)
    num_steps = len(status[0])
    ax.set_anchor("W")
    ax.set_aspect("equal")
    ax.set_title(f"Files _FXINP_lfrf<DDHH>0000_<mmm>{file_suffix}", loc="left")
    ax.set_xlabel("step")
    ax.set_xticks([x + 0.5 for x in range(num_steps)], labels=range(num_steps))
    ax.set_ylabel("member")
    ax.set_yticks([x + 0.5 for x in range(num_members)], labels=range(num_members))
    ax.pcolormesh(
        status, cmap=cmap, shading="flat", edgecolors="k", linewidths=1, vmin=0, vmax=1
    )


def plot_history(ax, history_status, history_datetime):
    # Plot the historical archival status.
    cmap = ListedColormap(["red", "green", "orange"])
    ax.set_anchor("W")
    ax.set_aspect("equal")
    ax.set_title("Historical archive status", loc="left")
    ax.set_xlabel("Archive date/time")
    ax.set_xticks(
        [x + 0.5 for x in range(len(history_datetime))], labels=history_datetime
    )
    ax.set_yticks([], [])
    ax.pcolormesh(
        [history_status],
        cmap=cmap,
        shading="flat",
        edgecolors="k",
        linewidths=1,
        vmin=0,
        vmax=2,
    )


def create_figure(collection: Collection):
    # Size the figure so the subplots have square boxes of the same size.
    boxes_per_inch = 2.5
    subplot_height = collection.members / boxes_per_inch
    # Use a larger box for the historical status to prevent the longer labels from overlapping.
    historical_box_size = 1.5
    # Add height for the historical plot and vertical spacing between subplots.
    plot_height = len(PARAMS) * subplot_height + historical_box_size + len(PARAMS)
    height_ratios = [subplot_height for _ in PARAMS]
    height_ratios.append(historical_box_size)
    plot_width = collection.steps / boxes_per_inch

    return plt.subplots(
        len(PARAMS) + 1,
        figsize=(plot_width, plot_height),
        gridspec_kw={"height_ratios": height_ratios},
        layout="constrained",
    )


def main(model: str) -> bool:
    collection = COLLECTIONS[model]
    last_run_start = last_run_time(collection, dt.datetime.now(dt.timezone.utc))
    latest_archive_status = get_archive_status(model, last_run_start)

    # For past forecasts, we have the full details already in previous runs. We only want to detect and alert if a
    # forecast is deleted early.
    history_status, history_datetime = historical_summary_status(
        last_run_start, collection
    )
    history_status.insert(0, summary_status(latest_archive_status))
    history_datetime.insert(0, last_run_start.strftime("%y%m%d%H00"))

    # Plot the archival status.
    fig, axs = create_figure(collection)
    fig.suptitle(
        f"Archival status for {model} run {last_run_start.strftime('%y%m%d%H00')}"
    )

    # Plot a status grid for each file suffix.
    for ax, param in zip(axs, PARAMS):
        plot_status(ax, latest_archive_status[param.file_suffix], param.file_suffix)

    plot_history(axs[len(PARAMS)], history_status, history_datetime)

    plt.savefig(
        f"heatmap_{model}_{last_run_start.strftime('%y%m%d%H00')}.png",
        bbox_inches="tight",
    )

    # If any files in the latest forecast failed, print the names and return failure.
    if history_status[0] != ForecastStatus.COMPLETE:
        logging.warning(
            "The following files failed to archive: %s",
            get_failed_files(latest_archive_status),
        )
        return False

    if any(status == ForecastStatus.MISSING for status in history_status):
        # Only report failure on missing forecast since an incomplete forecast will have
        # alerted us already.
        return False
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "model", type=str.lower, choices=["icon-ch1-eps", "icon-ch2-eps"]
    )
    args = parser.parse_args()

    if not main(args.model):
        sys.exit(1)
