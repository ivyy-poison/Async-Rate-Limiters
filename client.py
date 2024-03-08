import cProfile

import asyncio
from asyncio import Queue

from models import Counters
from logger import configure_logger
from workers import exchange_facing_worker_async as exchange_facing_worker, generate_requests
from config import VALID_API_KEYS
from utils import log_count_to_file


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


if __name__ == '__main__':
    profiler = cProfile.Profile()
    profiler.runcall(main)
    profiler.print_stats()
