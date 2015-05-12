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
    :param int period: minimal delay between two consecutive function invocation [seconds]
    :param int cooldown: delay to start next invocation after previous one finished [seconds]
    """
    def __init__(self, name, fn, period=0, cool_down=0):
        self.name = name
        self.fn = fn
        self.period = period
        self.cool_down = cool_down

    def can_start(self):
        raise NotImplementedError()


class Runner(object):
    def __init__(self, app):
        self.app = app
        self.loop = asyncio.get_event_loop()

        self.periodic_tasks = []
        # {name->latest start time (unixtime) }
        self.periodic_tasks_last_started = defaultdict(int)

        self.pool = ThreadPoolExecutor(2)
        # if we use dedicated processes we should setup centralized logging
        # self.pool = ProcessPoolExecutor(4)

        self.tick = 0

        self.is_running = False
        self.finishing_future = Future()

    def ticks(self):
        print("Current tick: {}".format(self.tick))
        self.tick += 1

    def add_periodic_task(self, name, task_fn, period):
        self.periodic_tasks.append((name, task_fn, period))


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
    def run_task_periodic(self, name, fn, period):
        log.info("Started periodic task: {}".format(name))
        while self.is_running:
            ft = self.loop.run_in_executor(self.pool, fn)
            start_time = time.time()
            log.debug("Executing task: {}".format(name))
            try:
                yield from ft  # now we cannot enforce timeout on task (
            except Exception:
                log.exception("Error during execution of {}".format(name))
            elapsed = time.time() - start_time
            log.debug("Task: {} finished in: {}".format(name, elapsed))
            delay = max(0, period - elapsed)
            if delay > 0 and self.is_running:
                yield from asyncio.sleep(delay)

    @coroutine
    def waiter(self):
        futures = [
            async(self.run_task_periodic(name, fn, period))
            for name, fn, period in self.periodic_tasks
        ]
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
        # self.loop.run_until_complete(self.waiter())
        self.loop.run_forever()

    @coroutine
    def stop(self):
        log.info("Stopping ")
        self.is_running = False
        yield from self.finishing_future
        log.info("Finished ")
        self.loop.stop()


def fa(*args, **kwargs):
    from datetime import datetime#
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
    r.add_periodic_task("A", fa, 0.02)
    r.add_periodic_task("B", fb, 0.01)
    # r.add_periodic_task("C", fc, 5.0)
    r.start()



