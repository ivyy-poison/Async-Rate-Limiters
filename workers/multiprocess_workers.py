from multiprocessing import Queue
from counters import MultiProcessCounters as Counters
from models import Request, RateLimiterTimeout
from rate_limiters import MultithreadDequeRateLimiter as DequeRateLimiter
from utils import timestamp_ms
from config import PER_SEC_RATE, REQUEST_TTL_MS, VALID_API_KEYS
import requests
import time
import random

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

def exchange_facing_worker_test(url: str, api_key: str, queue: Queue, counters: Counters):
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
