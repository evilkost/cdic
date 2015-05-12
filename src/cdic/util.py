# coding: utf-8
import logging


def setup_logging(log_file_path):
    logging.basicConfig(
        filename=log_file_path,
        # stream=sys.stdout,
        # format='[%(asctime)s][%(name)s][PID: %(process)d][%(levelname)6s]: %(message)s',
        format='[%(asctime)s][%(threadName)10s][%(levelname)6s][%(name)s]: %(message)s',
        level=logging.DEBUG
    )

