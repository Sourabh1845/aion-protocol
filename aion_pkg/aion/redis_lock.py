import os

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")

try:
    import redis
    REDIS_CLIENT = redis.Redis(host=REDIS_HOST, port=6379, db=0)
    REDIS_CLIENT.ping()
    REDIS_AVAILABLE = True
    print("Redis connected successfully")
except Exception:
    REDIS_AVAILABLE = False
    print("Redis not available — using local lock fallback")

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
    
    # Fallback
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
    
    # Fallback
    _local_locks.discard(jti)

def test_redis_connection():
    return REDIS_CLIENT.ping() if REDIS_AVAILABLE else False