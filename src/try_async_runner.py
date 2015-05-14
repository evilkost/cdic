# coding: utf-8

import time
import logging

log = logging.getLogger(__name__)

from cdic.util import setup_logging
from cdic.app.async.runner import Runner
from cdic.app.async.task import OnDemandTask


def fa(*args, **kwargs):
    from datetime import datetime
    log.info("A: {}".format(datetime.now().isoformat()))


def fb(*args, **kwargs):
    from datetime import datetime
    import random
    if random.randint(0, 100) > 90:
        time.sleep(0.03)
    log.info("B: {}".format(datetime.now().isoformat()))


def echo(*args, **kwargs):
    log.info("Echo args: {}, kwargs: {}".format(args, kwargs))


if __name__ == "__main__":
    setup_logging("/tmp/cdic_async_tasks.log")

    r = Runner(None)

    # r.add_periodic_task(fc, None, None)
    r.add_periodic_task("A1", fa, 50)
    # r.add_periodic_task("A2", fa, 1, 50)
    # r.add_periodic_task("B", fb, 0.01)

    r.add_on_demand_task(OnDemandTask("echo", "echo:pubsub", echo, lambda msg: ((msg,), {})))

    r.start()
