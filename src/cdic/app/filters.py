# coding: utf-8

import datetime

import pytz

from . import app

#
# @app.template_filter('localized_time')
# def localized_time(time_in, timezone):
#     """ return time shifted into timezone (and printed in ISO format)
#
#     Input is in EPOCH (seconds since epoch).
#     """
#     if not time_in:
#         return "Not yet"
#     format_tz = "%Y-%m-%d %H:%M %Z"
#     utc_tz = pytz.timezone('UTC')
#     if timezone:
#         user_tz = pytz.timezone(timezone)
#     else:
#         user_tz = utc_tz
#     dt_aware = datetime.datetime.fromtimestamp(time_in).replace(tzinfo=utc_tz)
#     dt_my_tz = dt_aware.astimezone(user_tz)
#     return dt_my_tz.strftime(format_tz)


@app.template_filter('time_ago')
def time_ago(time_in: datetime) -> str:
    """ returns string saying how long ago the time on input was
    """
    now = datetime.datetime.utcnow()
    diff = now - time_in
    sec_diff = int(diff.total_seconds())

    rules = [
        # threshold in seconds, view function, suffix

        (120, lambda x: "", "<2 minutes"),
        (7200, lambda x: int(x / 60),  "minutes"),
        (172800, lambda x: int(x / 3600),  "hours"),
        (5184000, lambda x: int(x / 86400),  "days"),
        # we should provide timezone # but it doesn't really matter here
        (None, lambda x: time_in.date().isoformat(),  ""),

    ]

    for threshold, func, suffix in rules:
        if threshold is None or sec_diff < threshold:
            return "{} {}".format(func(sec_diff), suffix)
    else:
        raise RuntimeError("Unexpected error in time_ago filter,")

