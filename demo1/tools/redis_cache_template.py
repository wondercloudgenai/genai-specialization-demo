import functools
import inspect
import json
import logging
import pickle
import re
import time
import typing as _t

import redis
logger = logging.getLogger(__name__)


class RedisSerializer(object):
    """Default serializer for RedisCache."""

    @staticmethod
    def dumps(value: _t.Any, protocol: int = pickle.HIGHEST_PROTOCOL):
        """Dumps an object into a string for redis. By default it serializes
        integers as regular string and pickle dumps everything else.
        """
        if isinstance(value, (dict, list, tuple, set)):
            return json.dumps(value)
        else:
            return str(value)
        # return b"!" + pickle.dumps(value, protocol)

    @staticmethod
    def loads(value: str) -> _t.Any:
        """The reversal of :meth:`dump_object`. This might be called with
        None.
        """
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode()
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return str(value)
        # if value.startswith(b"!"):
        #     try:
        #         return pickle.loads(value[1:])
        #     except pickle.PickleError:
        #         return None
        # try:
        #     return int(value)
        # except ValueError:
        #     # before 0.8 we did not have serialization. Still support that.
        #     return value


class RedisCacheException(Exception):
    def __init__(self, value):
        self.value = value


class RedisCacheTemplate:
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix_key: str = None,
        default_cache_expire: int = 3600,
        **kwargs: _t.Any
    ):
        self.redis_url = redis_url
        self.serializer = RedisSerializer()
        self.prefix_key = prefix_key
        self.default_cache_expire = default_cache_expire
        self._write_client = self._read_client = self.redis_client = redis.from_url(redis_url, **kwargs)

    def _normalize_key(self, key) -> str:
        if self.prefix_key:
            return f"{self.prefix_key}{key}"
        return key

    def _normalize_expire(self, _expire: _t.Union[int, str, None]) -> _t.Optional[int]:
        if _expire is None or _expire == -1 or _expire == 0:
            return self.default_cache_expire
        if isinstance(_expire, str):
            match = re.match(r"^(\d+)([sSMmhHdD])$", _expire)
            if not match:
                raise RedisCacheException("Exception possibly due to cache backend, invalid expire time expression.")
            elif match.group(2) == "mM":
                return int(match.group(1)) * 60
            elif match.group(2) == "hH":
                return int(match.group(1)) * 3600
            elif match.group(2) == "dD":
                return int(match.group(1)) * 3600 * 24
            return int(match.group(1))

    def set(self, key: str, value: _t.Any, expire: int = None) -> _t.Any:
        dump = self.serializer.dumps(value)
        if expire == -1 or expire is None:
            result = self._write_client.set(name=self._normalize_key(key), value=dump)
        else:
            result = self._write_client.setex(name=self._normalize_key(key), value=dump, time=expire)
        return result

    def hset(self, name: str, key: str, value: _t.Any, expire: int = None) -> _t.Any:
        dump = self.serializer.dumps(value)
        result = self._write_client.hset(self._normalize_key(name), key, dump)
        if expire != -1 and expire is not None and result:
            self._write_client.expire(name, time=expire)
        return result

    def hget(self, name: str, key: str) -> _t.Any:
        return self.serializer.loads(self._read_client.hget(self._normalize_key(name), key))

    def get(self, key: str) -> _t.Any:
        return self.serializer.loads(self._read_client.get(self._normalize_key(key)))

    def set_many(self, mapping: _t.Dict[str, _t.Any], expire: _t.Optional[int] = None) -> _t.List[_t.Any]:
        # Use transaction=False to batch without calling redis MULTI
        # which is not supported by twemproxy
        pipe = self._write_client.pipeline(transaction=False)

        for key, value in mapping.items():
            dump = self.serializer.dumps(value)
            if expire == -1 or expire is None:
                pipe.set(self._normalize_key(key), value=dump)
            else:
                pipe.setex(name=self._normalize_key(key), value=dump, time=expire)
        results = pipe.execute()
        return [k for k, was_set in zip(mapping.keys(), results) if was_set]

    def get_many(self, *keys: str) -> _t.List[_t.Any]:
        keys = [self._normalize_key(key) for key in keys]
        return [self.serializer.loads(x) for x in self._read_client.mget(keys)]

    def delete(self, key: str) -> bool:
        return bool(self._write_client.delete(self._normalize_key(key)))

    def delete_many(self, *keys: str) -> _t.List[_t.Any]:
        if not keys:
            return []
        prefixed_keys = [self._normalize_key(k) for k in keys]
        self._write_client.delete(*prefixed_keys)
        return [k for k in prefixed_keys if not self.has(k)]

    def has(self, key: str) -> bool:
        return bool(self._read_client.exists(self._normalize_key(key)))

    def clear(self) -> bool:
        status = 0
        if self.prefix_key:
            keys = self._read_client.keys(self.prefix_key + "*")
            if keys:
                status = self._write_client.delete(*keys)
        else:
            status = self._write_client.flushdb()
        return bool(status)

    def inc(self, key: str, delta: int = 1) -> _t.Any:
        return self._write_client.incr(name=self._normalize_key(key), amount=delta)

    def dec(self, key: str, delta: int = 1) -> _t.Any:
        return self._write_client.incr(name=self._normalize_key(key), amount=-delta)

    def lpush(self, key: str, value: _t.Any) -> _t.Any:
        return self._write_client.lpush(self._normalize_key(key), value)

    def expire(self, key: str, expire: int) -> _t.Any:
        return self._write_client.expire(name=self._normalize_key(key), time=expire)

    def lall(self, key: str) -> _t.Any:
        return self._write_client.lrange(self._normalize_key(key), 0, -1)

    def lrem(self, key: str, value: _t.Any) -> _t.Any:
        return self._write_client.lrem(name=self._normalize_key(key), value=value, count=0)

    def cached(
        self,
        key: str,
        expire: _t.Union[int, str] = None,
        ignore_prefix_key: bool = True,
        unless: _t.Callable = None,
        cache_none: bool = False,
    ) -> _t.Callable:
        def decorator(f):
            @functools.wraps(f)
            def decorated_function(*args, **kwargs):
                #: get cache.
                if ignore_prefix_key:
                    _key = key
                else:
                    _key = self._normalize_key(key)

                try:
                    rv = self._read_client.get(_key)
                    found = True

                    # If the value returned by cache.get() is None, it
                    # might be because the key is not found in the cache
                    # or because the cached value is actually None
                    if rv is None:
                        # If we're sure we don't need to cache None values
                        # (cache_none=False), don't bother checking for
                        # key existence, as it can lead to false positives
                        # if a concurrent call already cached the
                        # key between steps. This would cause us to
                        # return None when we shouldn't
                        if not cache_none:
                            found = False
                        else:
                            found = self._read_client.has(_key)
                except Exception:
                    logger.exception("Exception possibly due to cache backend.")
                    return f(*args, **kwargs)

                if not found:
                    try:
                        rv = f(*args, **kwargs)
                        if inspect.isgenerator(rv):
                            rv = [val for val in rv]
                    except Exception:
                        raise
                    try:
                        _expire = self._normalize_expire(expire)
                        self._write_client.setex(
                            _key,
                            rv,
                            timeout=_expire,
                        )
                    except Exception:
                        logger.exception("Exception possibly due to cache backend.")
                return rv
            return decorated_function
        return decorator


if __name__ == "__main__":
    print(111)
    cache = RedisCacheTemplate()
    cache.hset("bingo", "value", {"key1": "value1", "key2": "value2"}, 10)
    print(cache.hget("bingo", "value"))
    time.sleep(5)
    cache.delete("bingo")
