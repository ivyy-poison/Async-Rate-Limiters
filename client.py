import sys
import os
import time
import random
import logging
import contextlib
from datetime import datetime
import collections

import asyncio
from asyncio import Queue
import aiohttp
import async_timeout


# region: DO NOT CHANGE - the code within this region can be assumed to be "correct"

PER_SEC_RATE = 20
DURATION_MS_BETWEEN_REQUESTS = int(1000 / PER_SEC_RATE)
REQUEST_TTL_MS = 1000
VALID_API_KEYS = ['UT4NHL1J796WCHULA1750MXYF9F5JYA6',
                  '8TY2F3KIL38T741G1UCBMCAQ75XU9F5O',
                  '954IXKJN28CBDKHSKHURQIVLQHZIEEM9',
                  'EUU46ID478HOO7GOXFASKPOZ9P91XGYS',
                  '46V5EZ5K2DFAGW85J18L50SGO25WJ5JE']


async def generate_requests(queue: Queue):
    """
    co-routine responsible for generating requests

    :param queue:
    :param logger:
    :return:
    """
    curr_req_id = 0
    MAX_SLEEP_MS = 1000 / PER_SEC_RATE / len(VALID_API_KEYS) * 1.05 * 2.0
    while True:
        queue.put_nowait(Request(curr_req_id))
        curr_req_id += 1
        sleep_ms = random.randint(0, MAX_SLEEP_MS)
        await asyncio.sleep(sleep_ms / 1000.0)


def timestamp_ms() -> int:
    return int(time.time() * 1000)

# endregion

class RateLimiterTimeout(Exception):
    pass

class RateLimiter:
    def __init__(self, per_second_rate, min_duration_ms_between_requests):
        self.__per_second_rate = per_second_rate
        self.__min_duration_ms_between_requests = min_duration_ms_between_requests
        self.__last_request_time = 0
        self.__request_times = [0] * per_second_rate
        self.__curr_idx = 0

    @contextlib.asynccontextmanager
    async def acquire(self, timeout_ms=0):
        enter_ms = timestamp_ms()
        while True:
            now = timestamp_ms()
            if now - enter_ms > timeout_ms > 0:
                raise RateLimiterTimeout()

            if now - self.__last_request_time <= self.__min_duration_ms_between_requests:
                await asyncio.sleep(0.001)
                continue

            if now - self.__request_times[self.__curr_idx] <= 1000:
                await asyncio.sleep(0.001)
                continue

            break

        self.__last_request_time = self.__request_times[self.__curr_idx] = now
        self.__curr_idx = (self.__curr_idx + 1) % self.__per_second_rate
        yield self

class DequeRateLimiter:
    def __init__(self, per_second_rate, min_duration_ms_between_requests):
        self.__per_second_rate = per_second_rate
        self.__min_duration_ms_between_requests = min_duration_ms_between_requests
        self.__request_times = collections.deque(maxlen=per_second_rate)
        self.__delay = 0.15 / per_second_rate  

    @contextlib.asynccontextmanager
    async def acquire(self, timeout_ms=0):
        enter_ms = timestamp_ms()
        while True:
            now = timestamp_ms()
            if timeout_ms > 0 and now - enter_ms > timeout_ms:
                raise RateLimiterTimeout()

            # Remove timestamps older than 1 second
            while self.__request_times and now - self.__request_times[0] > 1000:
                self.__request_times.popleft()

            # If the rate limit has been hit, sleep until the next request can be made
            if len(self.__request_times) >= self.__per_second_rate:
                sleep_time = (self.__request_times[0] + 1000 - now) / 1000
                await asyncio.sleep(sleep_time)
            else:
                break

        self.__request_times.append(now)
        await asyncio.sleep(self.__delay)
        yield self


class TokenBucketRateLimiter:
    def __init__(self, tokens, min_duration_ms_between_requests):
        fill_rate = min_duration_ms_between_requests

        self.capacity = tokens
        self._tokens = tokens
        self.fill_rate = float(fill_rate)
        self.timestamp = time.time()

    def _refill(self):
        now = time.time()
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
                await asyncio.sleep(1.0)  # sleep for the calculated sleep_time
        yield


def configure_logger(name=None):
    logger = logging.getLogger(name)
    if name is None:
        # only add handlers to root logger
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)
        logger.addHandler(sh)

        fh = logging.FileHandler(f"async-debug.log", mode="a")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        logger.setLevel(logging.DEBUG)
    return logger








async def exchange_facing_worker(url: str, api_key: str, queue: Queue, logger: logging.Logger):
    global count, ignored_count, error_count
    rate_limiter = RateLimiter(PER_SEC_RATE, DURATION_MS_BETWEEN_REQUESTS)
    rate_limiter = DequeRateLimiter(PER_SEC_RATE, DURATION_MS_BETWEEN_REQUESTS)
    # rate_limiter = TokenBucketRateLimiter(PER_SEC_RATE, DURATION_MS_BETWEEN_REQUESTS)
    async with aiohttp.ClientSession() as session:
        while True:
            request: Request = await queue.get()
            remaining_ttl = REQUEST_TTL_MS - (timestamp_ms() - request.create_time)
            if remaining_ttl <= 0:
                logger.warning(f"ignoring request {request.req_id} from queue due to TTL")
                continue

            try:
                nonce = timestamp_ms()
                # async with rate_limiter.acquire(timeout_ms=remaining_ttl):
                async with rate_limiter.acquire() as limiter:
                    async with async_timeout.timeout(1.0):
                        data = {'api_key': api_key, 'nonce': nonce, 'req_id': request.req_id}
                        async with session.request('GET',
                                                   url,
                                                   data=data) as resp:  # type: aiohttp.ClientResponse
                            json = await resp.json()
                            if json['status'] == 'OK':
                                logger.info(f"API response: status {resp.status}, resp {json}")
                                count += 1
                            else:
                                error_count += 1
                                logger.warning(f"API response: status {resp.status}, resp {json}")
            except RateLimiterTimeout:
                logger.warning(f"ignoring request {request.req_id} in limiter due to TTL")
        

class Request:
    def __init__(self, req_id):
        self.req_id = req_id
        self.create_time = timestamp_ms()

count = 0
ignored_count = 0
error_count = 0

def main():


    url = "http://127.0.0.1:9999/api/request"
    loop = asyncio.get_event_loop()
    queue = Queue()

    logger = configure_logger()
    loop.create_task(generate_requests(queue=queue))

    for api_key in VALID_API_KEYS:
        loop.create_task(exchange_facing_worker(url=url, api_key=api_key, queue=queue, logger=logger))


    # loop.run_forever()
        
    # Run the event loop for 5 seconds
    loop.run_until_complete(asyncio.sleep(10))

    # Print the total number of successful requests
    log_count_to_file(count)

def log_count_to_file(count):
    # Check if the file exists
    if os.path.exists("output.txt"):
        # If it exists, read the existing content
        with open("output.txt", "r") as f:
            content = f.read()
    else:
        content = ""

    # Get the current time in a readable format
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Write the current time and count to the top of the file
    with open("output.txt", "w") as f:
        f.write(f"Current time: {current_time}, Successful requests: {count}, Ignored requests: {ignored_count}, 429 errors: {error_count}\n{content}")


if __name__ == '__main__':
    main()
