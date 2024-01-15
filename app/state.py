import logging
from functools import wraps

import redis.asyncio as redis
from redis import RedisError

from app.settings import REDIS_URL

STANDBY = 'STANDBY'
BUSY = 'BUSY'

pool = redis.ConnectionPool.from_url(REDIS_URL)
redis_client = redis.Redis.from_pool(pool)


def error_wrapper(async_func):
    @wraps(async_func)
    async def wrapper(*args, **kwargs):
        try:
            return await async_func(*args, **kwargs)
        except RedisError as e:
            logging.error(f'Could not perform redis operation. {str(e)}')
    return wrapper


@error_wrapper
async def init_app_state():
    result = await redis_client.set("request_counter", 0)
    return result


@error_wrapper
@error_wrapper
async def get_app_state():
    request_counter = await redis_client.get("request_counter")
    if int(request_counter):
        return BUSY
    return STANDBY


@error_wrapper
async def incr_app_state():
    result = await redis_client.incr("request_counter")
    return result


@error_wrapper
async def decr_app_state():
    result = await redis_client.decr("request_counter")
    return result
