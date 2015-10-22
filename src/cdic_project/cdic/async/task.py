# coding: utf-8
import json
import time


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


def json_params_parser(msg: str) -> tuple:
    """
    :param msg: serialized string
    :return: ([args], {kwargs})
    """
    raw = json.loads(msg)
    return raw["args"], raw["kwargs"]


def json_params_serializer(*args, **kwargs) -> str:
    return json.dumps({"args": args, "kwargs": kwargs})


class OnDemandTask(object):
    """
    Represents tasks activated through message queue.
    Firstly we setup task (function to invoke and function to parse mq payload)

    :param name: task name
    :param channel: name of the redis pub-sub channel to listen
    :param fn: Target function to execute on receiving particular message
    :param parser: Parser queue message into the `fn` parameters [msg => (args, kwargs)]
    """
    def __init__(self, name: str, channel: str, fn: callable,
                 parser: callable=None, serializer: callable=None):
        self.name = name
        self.channel = channel
        self.fn = fn

        self.parser = parser or json_params_parser
        self.serializer = serializer or json_params_serializer

