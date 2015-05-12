# coding: utf-8
from collections import defaultdict
import logging

import signal

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import asyncio
from asyncio import coroutine, async, Future
import time

from app.util.github import create_github_repo
from util import setup_logging


logging.getLogger("asyncio").setLevel(logging.WARN)
log = logging.getLogger(__name__)


class PeriodicTask(object):
    """
    :param name: task name
    :param fn: callable function
    :param period: minimal delay between two consecutive function invocation [seconds]
    :param cool_down: delay to start next invocation after previous one finished [seconds]
    """
    def __init__(self, name: str, fn: "callable", period: int=None, cool_down: int=None):
        self.name = name
        self.fn = fn
        self.period = period or 0
        self.cool_down = cool_down or 0

    def get_delay(self, prev_started: int, prev_finished: int) -> int:
        cur_time = time.time()
        since_start = cur_time - prev_started
        since_finish = cur_time - prev_finished
        delay = max(0, self.period - since_start, self.cool_down - since_finish)
        return delay


class Runner(object):
    def __init__(self, app):
        self.app = app
        self.loop = asyncio.get_event_loop()

        self.periodic_tasks = []

        self.pool = ThreadPoolExecutor(6)
        # if we use dedicated processes we should setup centralized logging
        # self.pool = ProcessPoolExecutor(4)

        self.is_running = False
        self.finishing_future = Future()

    def add_periodic_task(self, name, task_fn, period, cool_down=None):
        self.periodic_tasks.append(PeriodicTask(name, task_fn, period, cool_down))

    # @coroutine
    # def schedule_periodic_task(self, name, fn, period):
    #     ft = self.loop.run_in_executor(self.pool, fn)
    #     """ :type : Future """
    #     @coroutine
    #     def continuation():
    #         yield from async.sleep(period)
    #         if self.is_running:
    #             self.loop.call_later(period,
    #                                  self.schedule_periodic_task(name, fn, period))
    #     ft.add_done_callback(async(continuation))
    #     yield from ft

    @coroutine
    def run_task_periodic(self, pt: PeriodicTask):
        log.info("Started periodic task: {}".format(pt.name))

        # while self.is_running:
        if self.is_running:
            ft = self.loop.run_in_executor(self.pool, pt.fn)
            start_time = time.time()
            log.debug("Executing task: {}".format(pt.name))
            try:
                yield from ft  # now we cannot enforce timeout on task (
            except Exception:
                log.exception("Error during execution of {}".format(pt.name))
            log.debug("Task: {} finished in: {}".format(pt.name,  time.time() - start_time))

            # next schedule next run
            if self.is_running:
                self.loop.call_later(pt.get_delay(start_time, time.time()),
                                     lambda: async(self.run_task_periodic(pt)))
                # delay = pt.get_delay(start_time, time.time())
                # if delay > 0 and self.is_running:
                #     yield from asyncio.sleep(delay)

    @coroutine
    def waiter(self):
        futures = [async(self.run_task_periodic(pt))
                   for pt in self.periodic_tasks]
        log.info("Spawned all periodic tasks")
        yield from asyncio.gather(*futures)
        log.info("Finished all periodic tasks")

        self.finishing_future.set_result("done")

    def attach_signal_handlers(self):
        for sig_name in ('SIGINT', 'SIGTERM'):
            self.loop.add_signal_handler(
                getattr(signal, sig_name),
                lambda: async(self.stop()))

    def start(self):
        self.attach_signal_handlers()
        self.is_running = True
        async(self.waiter())
        self.loop.run_forever()

    @coroutine
    def stop(self):
        log.info("Stopping ")
        self.is_running = False
        yield from self.finishing_future
        log.info("Finished ")
        self.loop.stop()


def fa(*args, **kwargs):
    from datetime import datetime
    log.info("A: {}".format(datetime.now().isoformat()))


def fb(*args, **kwargs):
    from datetime import datetime
    import random
    if random.randint(0, 100) > 90:
        time.sleep(0.03)
    log.info("B: {}".format(datetime.now().isoformat()))


def fc(*args, **kwargs):

    from app import app
    with app.app_context():
        from app.internal_api import Api
        api = Api()
        create_github_repo(api)

if __name__ == "__main__":
    setup_logging("/tmp/cdic_async_tasks.log")

    r = Runner(None)

    # r.add_periodic_task(fc, None, None)
    r.add_periodic_task("A1", fa, 1)
    r.add_periodic_task("A2", fa, 1, 50)
    # r.add_periodic_task("B", fb, 0.01)
    # r.add_periodic_task("C", fc, 5.0)
    r.start()



