# coding: utf-8
import datetime
import logging
import pytz


def setup_logging(log_file_path=None):
    logging.basicConfig(
        filename=log_file_path,
        # stream=sys.stdout,
        # format='[%(asctime)s][%(name)s][PID: %(process)d][%(levelname)6s]: %(message)s',
        format='[%(asctime)s][%(threadName)10s][%(levelname)6s][%(name)s]: %(message)s',
        level=logging.DEBUG
    )

def utc_now():
    """
    :return datetime.datetime: Current utc datetime with specified timezone
    """
    u = datetime.datetime.utcnow()
    u = u.replace(tzinfo=pytz.utc)
    return u
