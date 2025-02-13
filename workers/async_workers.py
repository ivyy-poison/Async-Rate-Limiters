import logging
from asyncio import Queue
import aiohttp
import asyncio
import random
import async_timeout
from counters import Counters
from request import Request
from rate_limiters import DequeRateLimiter, CircularArrayRateLimiter, TokenBucketRateLimiter, OriginalRateLimiter
from utils import timestamp_ms
from config import VALID_API_KEYS, REQUEST_TTL_MS, PER_SEC_RATE

async def generate_requests(queue: Queue) -> None:
    """
    A long-runnning co-routine responsible for generating HTTP requests and putting them into a queue.

    :param queue: an asyncio.Queue object to put requests into
    """
    curr_req_id = 0
    MAX_SLEEP_MS = 1000 / PER_SEC_RATE / len(VALID_API_KEYS) * 1.05 * 2.0
    while True:
        queue.put_nowait(Request(curr_req_id))
        curr_req_id += 1
        sleep_ms = random.randint(0, MAX_SLEEP_MS)
        await asyncio.sleep(sleep_ms / 1000.0)


async def exchange_facing_worker(url: str, api_key: str, queue: Queue, logger: logging.Logger, counters: Counters):
    rate_limiter = OriginalRateLimiter(PER_SEC_RATE)
    rate_limiter = CircularArrayRateLimiter(PER_SEC_RATE)
    rate_limiter = DequeRateLimiter(PER_SEC_RATE)

    async with aiohttp.ClientSession() as session:
        while True:
            request: Request = await queue.get()
            remaining_ttl = REQUEST_TTL_MS - (timestamp_ms() - request.create_time)

            if remaining_ttl <= 0:
                counters.increment_ignored_count()
                logger.warning(f"ignoring request {request.req_id} from queue due to TTL")
                continue

            try:
                nonce = timestamp_ms()
                async with rate_limiter.acquire():
                    async with async_timeout.timeout(1.0):
                        data = {'api_key': api_key, 'nonce': nonce, 'req_id': request.req_id}
                        async with session.request('GET',
                                                   url,
                                                   data=data) as resp: 
                            json = await resp.json()
                            if json['status'] == 'OK':
                                logger.info(f"API response: status {resp.status}, resp {json}")
                                counters.increment_count()
                            else:
                                counters.increment_error_count()
                                logger.warning(f"API response: status {resp.status}, resp {json}")
            except Exception as e:
                counters.increment_error_count()
                logger.warning(f"Exception: {e}")

