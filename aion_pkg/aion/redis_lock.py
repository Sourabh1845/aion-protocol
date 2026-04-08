import os

REDIS_URL = os.environ.get("REDIS_URL")

try:
    import redis
    if REDIS_URL:
        REDIS_CLIENT = redis.from_url(REDIS_URL, ssl_cert_reqs=None)
    else:
        REDIS_CLIENT = redis.Redis(host="localhost", port=6379, db=0)
    REDIS_CLIENT.ping()
    REDIS_AVAILABLE = True
    print("Redis connected successfully")
except Exception as e:
    REDIS_AVAILABLE = False
    print(f"Redis not available — using local lock fallback: {e}")

# Fallback in-memory lock
_local_locks = set()

def acquire_redis_lock(jti: str, ttl_seconds: float = 5.0) -> bool:
    if REDIS_AVAILABLE:
        try:
            lock_key = f"aion:lock:{jti}"
            acquired = REDIS_CLIENT.set(
                lock_key,
                "locked",
                nx=True,
                ex=int(ttl_seconds)
            )
            return acquired is True
        except Exception:
            pass
    if jti in _local_locks:
        return False
    _local_locks.add(jti)
    return True

def release_redis_lock(jti: str):
    if REDIS_AVAILABLE:
        try:
            lock_key = f"aion:lock:{jti}"
            REDIS_CLIENT.delete(lock_key)
            return
        except Exception:
            pass
    _local_locks.discard(jti)

def test_redis_connection():
    return REDIS_CLIENT.ping() if REDIS_AVAILABLE else False