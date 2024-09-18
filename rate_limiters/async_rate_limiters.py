import contextlib
import asyncio
import collections
from utils import timestamp_ms
from .base import BaseRateLimiter
import contextlib
from contextlib import asynccontextmanager

class OriginalRateLimiter(BaseRateLimiter):
    def __init__(self, per_second_rate):
        self.__per_second_rate = per_second_rate
        self.__min_duration_ms_between_requests = int(1000 / per_second_rate)
        self.__last_request_time = 0
        self.__request_times = [0] * per_second_rate
        self.__curr_idx = 0

    @contextlib.asynccontextmanager
    async def acquire(self):
        while True:
            now = timestamp_ms()

            if now - self.__last_request_time <= self.__min_duration_ms_between_requests:
                await asyncio.sleep(( self.__min_duration_ms_between_requests - (now - self.__last_request_time) ) / 1000) 
                continue

            if now - self.__request_times[self.__curr_idx] <= 1000:
                await asyncio.sleep((1000 - (now - self.__request_times[self.__curr_idx])) / 1000)
                continue

            break

        self.__last_request_time = self.__request_times[self.__curr_idx] = now
        self.__curr_idx = (self.__curr_idx + 1) % self.__per_second_rate
        yield self


class CircularArrayRateLimiter(BaseRateLimiter):
    def __init__(self, per_second_rate):
        self.__per_second_rate = per_second_rate
        self.__request_times = [0] * per_second_rate
        self.__curr_idx = 0

    @contextlib.asynccontextmanager
    async def acquire(self):
        try:
            while True:
                now = timestamp_ms()

                if now - self.__request_times[self.__curr_idx] <= 1000:
                    await asyncio.sleep((1000 - (now - self.__request_times[self.__curr_idx])) / 1000)
                    continue

                break
            yield self
        finally:
            self.__request_times[self.__curr_idx] = timestamp_ms()
            self.__curr_idx = (self.__curr_idx + 1) % self.__per_second_rate


class DequeRateLimiter(BaseRateLimiter):
    def __init__(self, per_second_rate):
        self.__per_second_rate = per_second_rate
        self.__request_times = collections.deque(maxlen=per_second_rate)

    @contextlib.asynccontextmanager
    async def acquire(self):
        try:
            now = timestamp_ms()

            while len(self.__request_times) > 0 and now - self.__request_times[0] >= 1000:
                self.__request_times.popleft()

            if len(self.__request_times) >= self.__per_second_rate:
                
                oldest_request_time = self.__request_times[0]
                time_to_wait = 1000 - (now - oldest_request_time)

                await asyncio.sleep(time_to_wait / 1000)
            yield self
        finally:
            self.__request_times.append(timestamp_ms())


class TokenBucketRateLimiter:
    def __init__(self, tokens, min_duration_ms_between_requests):
        fill_rate = min_duration_ms_between_requests
        self.capacity = tokens
        self._tokens = tokens - 1
        self.fill_rate = float(fill_rate)
        self.timestamp = timestamp_ms()

    def _refill(self):
        now =  timestamp_ms()
        delta = now - self.timestamp
        refill = self.fill_rate * delta
        self._tokens = min(self.capacity, self._tokens + refill)
        self.timestamp = now

    @contextlib.asynccontextmanager
    async def acquire(self, tokens=1):
        if tokens < 0:
            raise ValueError("Number of tokens to acquire must be non-negative")
        while True:
            self._refill()
            if tokens <= self._tokens:
                self._tokens -= tokens
                break
            else:
                sleep_time = (tokens - self._tokens) / self.fill_rate
                continue
        yield