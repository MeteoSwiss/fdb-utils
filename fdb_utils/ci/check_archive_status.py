import argparse
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import IntEnum

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

from fdb_utils.user.describe import list_all_values


@dataclass
class Collection:
    members: int
    steps: int
    forecasts: int
    interval: int


@dataclass
class Parameter:
    key: str
    file_suffix: str
    is_constant: bool
    filter: dict[str, str]


# The ICON forecast GRIB files are separated by step, number, and suffix. The poller archives each file such that an
# error will result in all data for the file missing. Thus we can check that all steps and members are present for a
# single parameter that exists in the file to determine the status.
#
# The poller archives the hourly rotlatlon grib files for constant params (suffix 'c'), single and multi level params
# (no suffix), and params on pressure levels (suffix 'p'). For details on what each file type means, see:
# https://meteoswiss.atlassian.net/wiki/spaces/APN/pages/412975206/ICON-22+PP+Naming+scheme+for+intermediate+products#TC-tasks%2C-prepare-step
COLLECTIONS: dict[str, Collection] = {
    "icon-ch1-eps": Collection(
        members=11,
        steps=33,
        forecasts=8,
        interval=3,
    ),
    "icon-ch2-eps": Collection(
        members=21,
        steps=121,
        forecasts=4,
        interval=6,
    ),
}


PARAMS: list[Parameter] = [
    Parameter(
        key="500004", file_suffix="c", is_constant=True, filter={"levtype": "sfc"}
    ),
    Parameter(
        key="500006",
        file_suffix="p",
        is_constant=False,
        filter={"levelist": "200", "levtype": "pl"},
    ),
    Parameter(
        key="500001",
        file_suffix="",
        is_constant=False,
        filter={"levelist": "1", "levtype": "ml"},
    ),
]


def fx_filename(suffix: str, member: int, step: int) -> str:
    """Construct the ICON fxshare filename for the provided parameters."""
    filename_template = "_FXINP_lfrf{dd:02}{hh:02}000_{mmm:03}"
    days = step // 24
    hours = step % 24
    filename = filename_template.format(dd=days, hh=hours, mmm=member) + suffix
    return filename


def get_archive_status(
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
    filter_values = {"param": param.key, "model": model, "date": date, "time": time}

    status = []
    for member in range(num_members):
        filter = filter_values
        filter["number"] = str(member)
        filter |= param.filter
        steps_present = list_all_values(*["step"], **filter).get("step", [])
        steps_status = [1 if str(s) in steps_present else 0 for s in range(num_steps)]
        status.append(steps_status)

    return status


class ForecastStatus(IntEnum):
    MISSING = 0
    COMPLETE = 1
    INCOMPLETE = 2


def overall_status(status_dict: dict[list[list[int]]]) -> ForecastStatus:
    """Determine the archival status of the forecast as a whole."""
    any_success = False
    all_success = True
    for status in status_dict.values():
        any_success |= any([any(steps_stat) for steps_stat in status])
        all_success &= all([all(steps_stat) for steps_stat in status])

    if all_success:
        return ForecastStatus.COMPLETE
    if any_success:
        return ForecastStatus.INCOMPLETE
    return ForecastStatus.MISSING


def plot_status(ax, cmap, status: list[list[int]], file_suffix: str):
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
        status, cmap=cmap, shading="flat", edgecolors="k", linewidths=1, vmin=0, vmax=2
    )


def main(model: str) -> bool:
    collection = COLLECTIONS[model]
    # The model runs at fixed intervals starting at hour 0 UTC each day.
    # Note, the ICON-CH1-EPS forecast should be fully archived 2.5 hours after the run start and ICON-CH2-EPS 3.5 hours
    # after. The script should be run at times accordingly.
    cur_timestamp = datetime.now(timezone.utc).timestamp()
    run_interval = collection.interval * 60 * 60
    last_run_ts = cur_timestamp // run_interval * run_interval
    last_run_start = datetime.fromtimestamp(last_run_ts, tz=timezone.utc)
    date_str = last_run_start.strftime("%Y%m%d")
    time_str = last_run_start.strftime("%H00")

    # Check that each file has been archived. Each file is a triple of param, number, and step.
    archive_status = dict()
    failed_files = []
    for p in PARAMS:
        param_status = get_archive_status(model, p, date_str, time_str)
        archive_status[p.file_suffix] = param_status
        for member, steps_status in enumerate(param_status):
            for step, success in enumerate(steps_status):
                if not success:
                    failed_files.append(fx_filename(p.file_suffix, member, step))

    # For past forecasts, only record their overall status since we have the full details already in previous runs.
    # This will detect if a forecast is deleted early.
    history_status = [overall_status(archive_status)]
    history_datetime = [date_str + time_str]
    past_start = last_run_start
    for past_forecast in range(1, collection.forecasts):
        past_start = past_start - timedelta(hours=collection.interval)
        past_date_str = past_start.strftime("%Y%m%d")
        past_time_str = past_start.strftime("%H00")
        past_status = dict()
        for p in PARAMS:
            param_status = get_archive_status(model, p, past_date_str, past_time_str)
            past_status[p.file_suffix] = param_status
        history_status.append(overall_status(past_status))
        history_datetime.append(past_date_str + past_time_str)

    # Plot the archival status.
    #
    # Size the figure so the subplots have square boxes of the same size.
    boxes_per_inch = 2.5
    subplot_height = collection.members / boxes_per_inch
    # Use a larger box for the historical status to prevent the longer labels from overlapping.
    historical_box_size = 1.5
    # Add height for the historical plot and vertical spacing between subplots.
    plot_height = len(PARAMS) * subplot_height + historical_box_size + len(PARAMS)
    height_ratios = [subplot_height for p in PARAMS]
    height_ratios.append(historical_box_size)
    plot_width = collection.steps / boxes_per_inch

    fig, axs = plt.subplots(
        len(PARAMS) + 1,
        figsize=(plot_width, plot_height),
        gridspec_kw={"height_ratios": height_ratios},
        layout="constrained",
    )
    cmap = ListedColormap(["red", "green", "orange"])
    fig.suptitle(f"Archival status for {model} run {date_str} {time_str}")

    # Create a single grid for each file suffix.
    for ax, param in zip(axs, PARAMS):
        plot_status(ax, cmap, archive_status[param.file_suffix], param.file_suffix)

    # Plot the historical archival status.
    historical_ax = axs[len(PARAMS)]
    historical_ax.set_anchor("W")
    historical_ax.set_aspect("equal")
    historical_ax.set_title(f"Historical archive status", loc="left")
    historical_ax.set_xlabel("Archive date/time")
    historical_ax.set_xticks(
        [x + 0.5 for x in range(collection.forecasts)], labels=history_datetime
    )
    historical_ax.set_yticks([], [])
    historical_ax.pcolormesh(
        [history_status],
        cmap=cmap,
        shading="flat",
        edgecolors="k",
        linewidths=1,
        vmin=0,
        vmax=2,
    )

    plt.savefig(f"heatmap_{model}_{date_str}{time_str}.png", bbox_inches="tight")

    # Print the names of all files that failed archival.
    if len(failed_files) > 0:
        logging.warning("The following files failed to archive: %s", failed_files)
        return False

    for history_stat in history_status:
        if history_stat is ForecastStatus.MISSING:
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

    success = main(args.model)
    if not success:
        exit(1)
