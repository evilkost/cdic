# coding: utf-8
import json
import time


# class PeriodicTask(object):
#     """
#     :param name: task name
#     :param fn: callable function
#     :param period: minimal delay between two consecutive function invocation [seconds]
#     :param cool_down: delay to start next invocation after previous one finished [seconds]
#     """
#     def __init__(self, name: str, fn: callable, period: int=None, cool_down: int=None):
#         self.name = name
#         self.fn = fn
#         self.period = period or 0
#         self.cool_down = cool_down or 0
#
#     def get_delay(self, prev_started: int, prev_finished: int) -> int:
#         cur_time = time.time()
#         since_start = cur_time - prev_started
#         since_finish = cur_time - prev_finished
#         delay = max(0, self.period - since_start, self.cool_down - since_finish)
#         return delay


def json_params_parser(msg: str) -> tuple:
    """
    :param msg: serialized string
    :return: ([args], {kwargs})
    """
    raw = json.loads(msg)
    return raw["args"], raw["kwargs"]


def json_params_serializer(*args, **kwargs) -> str:
    return json.dumps({"args": args, "kwargs": kwargs})


class TaskDef(object):

    """
    Async Task Definition

    :param channel: name of the redis pub-sub channel to listen
    :param work_fn: Target function to execute on receiving particular message
    :param on_success: Function to execute after success
    :param on_error: Function to execute upon error
    :param reschedule_fn: Function to check if same task should be executed again
                          should return a list of pairs (*args, **kwargs), which would be
                          passed to serializer

    :param parser: Parser queue message into the `fn` parameters [msg -> (args, kwargs)]
    :param serializer: Serialize the `fn` parameters [(args, kwargs) -> msg] into the queue message
    """

    def __init__(self, channel: str,
                 work_fn: callable,
                 # on_success: callable, on_error: callable,
                 reschedule_fn: callable,
                 parser: callable=None, serializer: callable=None):
        self.channel = channel
        self.work_fn = work_fn
        # self.on_success = on_success
        # self.on_error = on_error
        self.reschedule_fn = reschedule_fn

        self.parser = parser or json_params_parser
        self.serializer = serializer or json_params_serializer

