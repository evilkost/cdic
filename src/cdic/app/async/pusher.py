# coding: utf-8
from functools import partial
import json

from .. import app

from ..util.redis import get_redis_connection
from .task import OnDemandTask

PREFIX = "cdic::"


def ctx_wrapper(fn):
    def wrapped(*args, **kwargs):
        with app.app_context():
            fn(*args, **kwargs)
    return wrapped


def schedule_task(task: OnDemandTask, *args, **kwargs):
    conn = get_redis_connection()
    payload = task.serializer(*args, **kwargs)
    conn.publish(task.channel, payload)
