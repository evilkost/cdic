# coding: utf-8

from functools import partial
import logging
import signal
import time

from concurrent.futures import ThreadPoolExecutor
import asyncio
from asyncio import coroutine, async, Future
import asyncio_redis

from .pusher import schedule_task_async
from .task import TaskDef

logging.getLogger("asyncio").setLevel(logging.WARN)
log = logging.getLogger(__name__)


# class Runner(object):
#     def __init__(self, app):
#         self.app = app
#         self.loop = asyncio.get_event_loop()
#
#         self.periodic_tasks = []  # List[PeriodicTask]
#         self.on_demand_tasks = {}  # {channel -> OnDemandTask}
#
#         self.pool = ThreadPoolExecutor(6)
#         # if we use dedicated processes we should setup centralized logging
#         # self.pool = ProcessPoolExecutor(4)
#         self.redis_connection = None
#
#         self.is_running = False
#
#     def add_periodic_task(self, name, task_fn, period, cool_down=None):
#         self.periodic_tasks.append(PeriodicTask(name, task_fn, period, cool_down))
#
#     def add_on_demand_task(self, task: OnDemandTask):
#         self.on_demand_tasks[task.channel] = task
#
#     @coroutine
#     def run_task_periodic(self, pt: PeriodicTask):
#         if self.is_running:
#             log.debug("Executing periodic task: {}".format(pt.name))
#             start_time = time.time()
#             try:
#                 ft = self.loop.run_in_executor(self.pool, pt.fn)
#                 yield from ft  # now we cannot enforce timeout on task (
#             except Exception:
#                 log.exception("Error during execution of {}".format(pt.name))
#             else:
#                 log.debug("Task: {} finished in: {}".format(pt.name,  time.time() - start_time))
#
#             # next schedule next run
#             if self.is_running:
#                 self.loop.call_later(pt.get_delay(start_time, time.time()),
#                                      lambda: async(self.run_task_periodic(pt)))
#
#     @coroutine
#     def handle_on_demand(self, odt: OnDemandTask, data: str):
#         try:
#             args, kwargs = odt.parser(data)
#         except Exception:
#             log.exception("Failed to parse message from channel: {}, raw data: {}"
#                           .format(odt.channel, data))
#             return
#
#         ft = self.loop.run_in_executor(self.pool, partial(odt.fn, *args, **kwargs))
#         start_time = time.time()
#         log.debug("Executing on demand task: {}".format(odt.name))
#         try:
#             yield from ft  # now we cannot enforce timeout on task (
#         except Exception:
#             log.exception("Error during execution of {}".format(odt.name))
#         log.debug("Task: {} finished in: {}".format(odt.name,  time.time() - start_time))
#
#     @coroutine
#     def subscribe_on_demand_tasks(self):
#         # todo: get host/port from app.config
#         self.redis_connection = yield from asyncio_redis.Connection.create()
#         # for channel, od_task in self.on_demand_tasks.items():
#         subscriber = yield from self.redis_connection.start_subscribe()
#         yield from subscriber.subscribe(list(self.on_demand_tasks.keys()))
#         while self.is_running:
#             reply = yield from subscriber.next_published()
#             log.debug('Received: `{}` on channel `{}`'
#                       .format(repr(reply.value), reply.channel))
#             odt = self.on_demand_tasks[reply.channel]
#             async(self.handle_on_demand(odt, reply.value))
#
#     # Runner daemonization below
#     @coroutine
#     def stop(self):
#         log.info("Stopping async runner ...")
#         self.is_running = False
#
#         self.pool.shutdown(wait=True)
#         self.loop.stop()
#
#         log.info("Finished ")
#
#     def attach_signal_handlers(self):
#         for sig_name in ('SIGINT', 'SIGTERM'):
#             self.loop.add_signal_handler(
#                 getattr(signal, sig_name),
#                 lambda: async(self.stop()))
#
#     def start(self):
#         self.attach_signal_handlers()
#         self.is_running = True
#         for pt in self.periodic_tasks:
#             async(self.run_task_periodic(pt))
#         async(self.subscribe_on_demand_tasks())
#         self.loop.run_forever()


class RunnerAlt(object):

    def __init__(self, app, loop=None):
        self.app = app
        self.loop = loop or asyncio.get_event_loop()

        self.pool = ThreadPoolExecutor(6)
        # if we use dedicated processes we should setup centralized logging
        # self.pool = ProcessPoolExecutor(4)
        self.redis_connection = None
        self.is_running = False
        self.tasks_spec = dict()  # todo: {channel -> TaskSpec}

        self.sleep_time = 120

    def get_channels_to_listen(self):
        return [tc.channel for tc in self.tasks_spec.values()]

    def register_task(self, td: TaskDef):
        self.tasks_spec[td.channel] = td

    @coroutine
    def dispatch_task(self, td: TaskDef, data: str):
        try:
            args, kwargs = td.parser(data)
        except Exception:
            log.exception("Failed to parse message from channel: {}, raw data: {}"
                          .format(td.channel, data))
            return

        ft = self.loop.run_in_executor(self.pool, partial(td.work_fn, *args, **kwargs))
        start_time = time.time()
        log.debug("Executing on demand task: {}".format(td.channel))
        try:
            yield from ft  # now we cannot enforce timeout on task (
        except Exception:
            log.exception("Error during execution of {}".format(td.channel))
        log.debug("Task: {} finished in: {}".format(td.channel,  time.time() - start_time))

    @coroutine
    def subscribe(self):
        # todo: get host/port from app.config
        # todo: create local wrapper for redis provider
        self.redis_connection = yield from asyncio_redis.Connection.create()
        # for channel, od_task in self.on_demand_tasks.items():
        subscriber = yield from self.redis_connection.start_subscribe()
        channels = self.get_channels_to_listen()
        log.info("Subscribing to the following channels: {}".format(channels))
        yield from subscriber.subscribe(channels)
        while self.is_running:
            reply = yield from subscriber.next_published()
            log.debug('Received: `{}` on channel `{}`'
                      .format(repr(reply.value), reply.channel))

            td = self.tasks_spec[reply.channel]
            async(self.dispatch_task(td, reply.value))

    @coroutine
    def check_for_reschedule(self):
        # todo: allow different sleep time for each task
        while self.is_running:

            for td in self.tasks_spec.values():

                async(self.check_reschedule(td))
            yield from asyncio.sleep(self.sleep_time)

    @coroutine
    def check_reschedule(self, td: TaskDef):
        ft = self.loop.run_in_executor(self.pool, td.reschedule_fn)
        to_reschedule = yield from ft
        log.info("check for pending reschedule for task: {}, items to resch:{}"
                 .format(td.channel, to_reschedule))
        # import ipdb; ipdb.set_trace()
        if to_reschedule:
            for args, kwargs in to_reschedule:
                schedule_task_async(td, *args, **kwargs)

    @coroutine
    def stop(self):
        log.info("Stopping async runner ...")
        self.is_running = False

        self.pool.shutdown(wait=True)
        self.loop.stop()

        log.info("Finished ")

    def attach_signal_handlers(self):
        for sig_name in ('SIGINT', 'SIGTERM'):
            self.loop.add_signal_handler(
                getattr(signal, sig_name),
                lambda: async(self.stop()))

    def start(self):
        self.attach_signal_handlers()
        self.is_running = True
        async(self.check_for_reschedule())
        async(self.subscribe())
        self.loop.run_forever()
