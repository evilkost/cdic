# coding: utf-8

from collections import defaultdict
from functools import partial
import logging
import signal
import time

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import asyncio
from asyncio import coroutine, async, Future


import asyncio_redis


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
    def __init__(self, name: str, fn: callable, period: int=None, cool_down: int=None):
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


class OnDemandTask(object):
    """
    Represents tasks activated through message queue.
    Firstly we setup task (function to invoke and function to parse mq payload)

    :param name: task name
    :param channel: name of the redis pub-sub channel to listen
    :param fn: Target function to execute on receiving particular message
    :param parser: Parser queue message into the `fn` parameters [msg => (args, kwargs)]
    """
    def __init__(self, name: str, channel: str, fn: callable, parser: callable=None):
        self.name = name
        self.channel = channel
        self.fn = fn

        def dummy_parser(msg):
            return (), {}
        self.parser = parser or dummy_parser


class Runner(object):
    def __init__(self, app):
        self.app = app
        self.loop = asyncio.get_event_loop()

        self.periodic_tasks = []  # List[PeriodicTask]
        self.on_demand_tasks = {}  # {channel -> OnDemandTask}

        self.pool = ThreadPoolExecutor(6)
        # if we use dedicated processes we should setup centralized logging
        # self.pool = ProcessPoolExecutor(4)
        self.redis_connection = None

        self.is_running = False
        self.finishing_future = Future()

    def add_periodic_task(self, name, task_fn, period, cool_down=None):
        self.periodic_tasks.append(PeriodicTask(name, task_fn, period, cool_down))

    def add_on_demand_task(self, name: str, channel: str, fn: callable, parser: callable=None):
        self.on_demand_tasks[channel] = OnDemandTask(name, channel, fn, parser)

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
    def handle_on_demand(self, odt: OnDemandTask, data: str):
        try:
            args, kwargs = odt.parser(data)
        except Exception:
            log.exception("Failed to parse message from channel: {}, raw data: {}"
                          .format(odt.channel, data))
            return

        ft = self.loop.run_in_executor(self.pool, partial(odt.fn, *args, **kwargs))
        start_time = time.time()
        log.debug("Executing on demand task: {}".format(odt.name))
        try:
            yield from ft  # now we cannot enforce timeout on task (
        except Exception:
            log.exception("Error during execution of {}".format(odt.name))
        log.debug("Task: {} finished in: {}".format(odt.name,  time.time() - start_time))



    @coroutine
    def subscribe_on_demand_tasks(self):
        # todo: get host/port from app.config
        self.redis_connection = yield from asyncio_redis.Connection.create()
        # for channel, od_task in self.on_demand_tasks.items():
        subscriber = yield from self.redis_connection.start_subscribe()
        yield from subscriber.subscribe(list(self.on_demand_tasks.keys()))
        while self.is_running:
            reply = yield from subscriber.next_published()
            log.debug('Received: `{}` on channel `{}`'
                      .format(repr(reply.value), reply.channel))
            odt = self.on_demand_tasks[reply.channel]
            async(self.handle_on_demand(odt, reply.value))

    # Runner daemonization below
    @coroutine
    def waiter(self):
        futures = [async(self.run_task_periodic(pt))
                   for pt in self.periodic_tasks]
        async(self.subscribe_on_demand_tasks())

        log.info("Add all tasks into the loop")
        yield from asyncio.gather(*futures)
        log.info("Finished all tasks")

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


def echo(*args, **kwargs):
    log.info("Echo args: {}, kwargs: {}".format(args, kwargs))


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
    r.add_periodic_task("A1", fa, 50)
    # r.add_periodic_task("A2", fa, 1, 50)
    # r.add_periodic_task("B", fb, 0.01)
    # r.add_periodic_task("C", fc, 5.0)

    r.add_on_demand_task("echo", "echo:pubsub", echo, lambda msg: ((msg,), {}))

    r.start()



