# coding: utf-8
from functools import partial
import json

from .. import app

from ..util.redis import get_redis_connection
from .task import TaskDef

PREFIX = "cdic::"


def ctx_wrapper(fn):
    def wrapped(*args, **kwargs):
        with app.app_context():
            return fn(*args, **kwargs)
    return wrapped


def schedule_task_async(task: TaskDef, *args, **kwargs):
    conn = get_redis_connection()
    payload = task.serializer(*args, **kwargs)
    conn.publish(task.channel, payload)
