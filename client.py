import os
import time
import random
from datetime import datetime
import cProfile

import asyncio
from asyncio import Queue
import aiohttp
import async_timeout

from models import Counters, Request, RateLimiterTimeout
from logger import configure_logger
from rate_limiters import DequeRateLimiter
from workers import exchange_facing_worker_async as exchange_facing_worker

from config import VALID_API_KEYS
from workers import generate_requests


def main():
    url = "http://127.0.0.1:9999/api/request"
    loop = asyncio.get_event_loop()
    queue = Queue()
    counters = Counters()

    logger = configure_logger()
    loop.create_task(generate_requests(queue=queue))

    for api_key in VALID_API_KEYS:
        loop.create_task(exchange_facing_worker(url=url, api_key=api_key, queue=queue, logger=logger, counters=counters))
    # loop.run_forever()
        
    # Run the event loop for 5 seconds
    loop.run_until_complete(asyncio.sleep(10))

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
    count, ignored_count, error_count = counters.count, counters.ignored_count, counters.error_count

    # Write the current time and count to the top of the file
    with open("output.txt", "w") as f:
        f.write(f"Current time: {current_time}, Successful requests: {count}, Ignored requests: {ignored_count}, 429 errors: {error_count}\n{content}")


if __name__ == '__main__':
    profiler = cProfile.Profile()
    profiler.runcall(main)
    profiler.print_stats()
