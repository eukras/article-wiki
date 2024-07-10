from datetime import datetime, timedelta

SECONDS_PER_DAY = 24 * 60 * 60


def day_in_last_fortnight(ts: int) -> int:
    """
    Number 0..13 for the past fourteen days, or None
    """
    index_time = datetime.fromtimestamp(ts)
    two_weeks_ago = datetime.now() - timedelta(days=14)
    if index_time < two_weeks_ago:
        return None
    return index_time.toordinal() - two_weeks_ago.toordinal()


def yyyymmdd_from_ts(ts: int) -> str:
    """
    No need to handle historical timezones; assume default.
    """
    return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
