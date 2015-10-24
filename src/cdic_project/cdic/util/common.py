# coding: utf-8
import datetime

from urllib.parse import urlparse
from dateutil.parser import parse as dt_parse
import pytz


def get_root_from_url(url: str) -> str:
    """
    :return: Url to the server root
    """
    parsed = urlparse(url)

    return


def dt_parse_to_utc_without_tz(val: str) -> datetime.datetime:
    tz = pytz.timezone("UTC")
    return dt_parse(val).astimezone(tz).replace(tzinfo=None)
