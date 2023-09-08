from datetime import datetime, timedelta, timezone
from typing import Optional


class StageNotFound(Exception):
    """No ongoing stage was found for the given date."""
    pass


def get_stage_dates(cfg_stage_dates: dict[str, str]) \
        -> dict[str, list[datetime]]:
    """
    Generate a list of datetime objects for
    every date range specified in <cfg_stage_dates>.
    """
    # TODO: force utc on the datetime objects?
    res: dict[str, list[datetime]] = {}

    for stage in cfg_stage_dates:

        start = cfg_stage_dates[stage].split(',')[0]
        end = cfg_stage_dates[stage].split(',')[1]

        start_date = datetime.strptime(start, '%Y-%m-%d')
        end_date = datetime.strptime(end, '%Y-%m-%d')

        current_date = start_date
        interval = timedelta(days=1)
        while current_date <= end_date:
            if stage in res:
                res[stage].append(current_date)
            else:  # occurs on first iteration
                res[stage] = [current_date]

            current_date += interval

    return res


def get_stage(stage_dates: dict[str, list[datetime]],
              date: datetime) -> Optional[str]:
    """Return the stage during <date>."""
    for stage in stage_dates:
        stage_start = stage_dates[stage][0]
        stage_end = stage_dates[stage][-1]
        if stage_start <= date <= stage_end:
            return stage


def weekday_to_dt(stage_dates: dict[str, list[datetime]],
                  reference_date: datetime,
                  weekday: int,
                  hour: int,
                  minute: int = 0) -> datetime:
    """
    Return the datetime object for <weekday>, <hour> and <min>
    based on <reference_date>.
    """
    # determine which date range to search in
    stage = get_stage(stage_dates, reference_date)
    if not stage:
        raise StageNotFound

    # search for the base datetime object with the weekday
    # should be guaranteed to find because of config validation
    for dt in stage_dates[stage]:
        if dt.weekday() == weekday:
            base_dt = dt

    # TODO: let tournament host pick timezone?
    return base_dt.replace(hour=hour, minute=minute, tzinfo=timezone.utc)
