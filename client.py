import cProfile

import asyncio
from asyncio import Queue

from models import Counters
from logger import configure_logger
from workers import exchange_facing_worker_async as exchange_facing_worker, generate_requests
from config import VALID_API_KEYS, SERVER_PORT, ENDPOINT_STUB
from utils import log_count_to_file


def main():
    url = f"http://localhost:{SERVER_PORT}{ENDPOINT_STUB}"
    loop = asyncio.get_event_loop()
    queue = Queue()
    counters = Counters()

    logger = configure_logger()
    loop.create_task(generate_requests(queue=queue))

    for api_key in VALID_API_KEYS:
        loop.create_task(exchange_facing_worker(url=url, api_key=api_key, queue=queue, logger=logger, counters=counters))
    
    # Original implementation was to run the event loop forever
    # loop.run_forever()
        
    # For testing purposes, we run the event loop for 10 seconds, then log the result to output.txt
    loop.run_until_complete(asyncio.sleep(10))
    log_count_to_file(counters)


if __name__ == '__main__':
    # profiler = cProfile.Profile()
    # profiler.runcall(main)
    # profiler.print_stats()
    main()
