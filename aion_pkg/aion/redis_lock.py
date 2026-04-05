import redis
import time
import uuid
import os
REDIS_CLIENT = redis.Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=6379,
    db=0
)

def acquire_redis_lock(jti: str, ttl_seconds: float = 5.0) -> bool:
    lock_key = f"aion:lock:{jti}"
    acquired = REDIS_CLIENT.set(
        lock_key,
        "locked",
        nx=True,
        ex=int(ttl_seconds)
    )
    return acquired is True

def release_redis_lock(jti: str):
    lock_key = f"aion:lock:{jti}"
    REDIS_CLIENT.delete(lock_key)

def test_redis_connection():
    return REDIS_CLIENT.ping()