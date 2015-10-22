# coding: utf-8

from redis import StrictRedis

from .. import app


def get_redis_connection():
    host = app.config.get("REDIS_HOST", "localhost")
    port = app.config.get("REDIS_PORT", 6379)
    return StrictRedis(host=host, port=port)
