import contextlib
import collections
from utils import timestamp_ms
import time
from models import RateLimiterTimeout

class DequeRateLimiter:
    def __init__(self, per_second_rate):
        self.__per_second_rate = per_second_rate
        self.__request_times = collections.deque(maxlen=per_second_rate)

    @contextlib.contextmanager
    def acquire(self, timeout_ms=0):
        now = timestamp_ms()

        while len(self.__request_times) > 0 and now - self.__request_times[0] >= 1000:
            self.__request_times.popleft()

        if len(self.__request_times) >= self.__per_second_rate-1:
            oldest_request_time = self.__request_times[0]
            time_to_wait = 1000 - (now - oldest_request_time)

            if timeout_ms > 0 and time_to_wait > timeout_ms:
                raise RateLimiterTimeout()

            time.sleep(time_to_wait / 1000)

        self.__request_times.append(timestamp_ms())
        yield