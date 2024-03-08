# Standard library imports
import collections
import contextlib
import cProfile
from datetime import datetime
from multiprocessing import Process, Queue, Value
import os
import random
import time

# Third-party libraries
import aiohttp
import asyncio
import requests
from models import MultithreadedCounters as Counters




# region: DO NOT CHANGE - the code within this region can be assumed to be "correct"

PER_SEC_RATE = 20
DURATION_MS_BETWEEN_REQUESTS = int(1000 / PER_SEC_RATE)
REQUEST_TTL_MS = 1000
VALID_API_KEYS = ['UT4NHL1J796WCHULA1750MXYF9F5JYA6',
                  '8TY2F3KIL38T741G1UCBMCAQ75XU9F5O',
                  '954IXKJN28CBDKHSKHURQIVLQHZIEEM9',
                  'EUU46ID478HOO7GOXFASKPOZ9P91XGYS',
                  '46V5EZ5K2DFAGW85J18L50SGO25WJ5JE']

class RateLimiterTimeout(Exception):
    pass

class Request:
    def __init__(self, req_id):
        self.req_id = req_id
        self.create_time = timestamp_ms()

def generate_requests(queue: Queue):
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
        time.sleep(sleep_ms / 1000.0)


def timestamp_ms() -> int:
    return int(time.time() * 1000)

# endregion

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

def exchange_facing_worker(url: str, api_key: str, queue: Queue, counters: Counters):
    rate_limiter = DequeRateLimiter(PER_SEC_RATE)

    while True:
        request: Request = queue.get()
        remaining_ttl = REQUEST_TTL_MS - (timestamp_ms() - request.create_time)
        if remaining_ttl <= 0:
            counters.increment_ignored_count()
            continue

        try:
            nonce = timestamp_ms()
            with rate_limiter.acquire():
                data = {'api_key': api_key, 'nonce': nonce, 'req_id': request.req_id}
                resp = requests.get(url, params=data)
                json = resp.json()
                if json['status'] == 'OK':
                    counters.increment_count()
                else:
                    counters.increment_error_count()
        except RateLimiterTimeout:
            counters.increment_ignored_count()

def exchange_facing_worker(url: str, api_key: str, queue: Queue, counters: Counters):
    rate_limiter = DequeRateLimiter(PER_SEC_RATE)
    start_time = time.time()

    while time.time() - start_time < 10:
        request: Request = queue.get()
        remaining_ttl = REQUEST_TTL_MS - (timestamp_ms() - request.create_time)
        if remaining_ttl <= 0:
            counters.increment_ignored_count()
            continue

        try:
            nonce = timestamp_ms()
            with rate_limiter.acquire():
                data = {'api_key': api_key, 'nonce': nonce, 'req_id': request.req_id}
                resp = requests.get(url, params=data)
                json = resp.json()
                if json['status'] == 'OK':
                    counters.increment_count()
                else:
                    counters.increment_error_count()
        except RateLimiterTimeout:
            counters.increment_ignored_count()

# async def fetch(session, url, data):
#     async with session.get(url, params=data) as response:
#         return await response.json()

# async def exchange_facing_worker_async(url: str, api_key: str, queue: Queue, counters: Counters):
#     rate_limiter = DequeRateLimiter(PER_SEC_RATE)
#     start_time = time.time()

#     async with aiohttp.ClientSession() as session:
#         while time.time() - start_time < 10:
#             request: Request = queue.get()
#             remaining_ttl = REQUEST_TTL_MS - (timestamp_ms() - request.create_time)
#             if remaining_ttl <= 0:
#                 counters.increment_ignored_count()
#                 continue

#             try:
#                 nonce = timestamp_ms()
#                 with rate_limiter.acquire():
#                     data = {'api_key': api_key, 'nonce': nonce, 'req_id': request.req_id}
#                     json = await fetch(session, url, data)
#                     if json['status'] == 'OK':
#                         counters.increment_count()
#                     else:
#                         counters.increment_error_count()
#             except RateLimiterTimeout:
#                 counters.increment_ignored_count()

# def exchange_facing_worker(url: str, api_key: str, queue: Queue, counters: Counters):
#     loop = asyncio.new_event_loop()
#     asyncio.set_event_loop(loop)
#     loop.run_until_complete(exchange_facing_worker_async(url, api_key, queue, counters))
#     loop.close()


def main():
    url = "http://127.0.0.1:9999/api/request"
    counters = Counters()

    # Create a queue for inter-process communication
    queue = Queue()

    # Start the request generator process
    request_generator = Process(target=generate_requests, args=(queue,))
    request_generator.start()

    # Start a worker process for each API key
    workers = []
    for api_key in VALID_API_KEYS:
        worker = Process(target=exchange_facing_worker, args=(url, api_key, queue, counters))
        worker.start()
        workers.append(worker)

    # Wait for all processes to finish
    
    for worker in workers:
        worker.join()

    request_generator.terminate()
    # Print the total number of successful requests
    log_count_to_file(counters)

def log_count_to_file(counters):
    # Check if the file exists
    if os.path.exists("output.txt"):
        # If it exists, read the existing content
        with open("output.txt", "r") as f:
            content = f.read()
    else:
        content = ""

    # Get the current time in a readable format
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count, ignored_count, error_count = counters.count.value, counters.ignored_count.value, counters.error_count.value

    # Write the current time and count to the top of the file
    with open("output.txt", "w") as f:
        f.write(f"Current time: {current_time}, Successful requests: {count}, Ignored requests: {ignored_count}, 429 errors: {error_count}\n{content}")


if __name__ == '__main__':
    profiler = cProfile.Profile()
    profiler.runcall(main)
    profiler.print_stats()
