# Standard library imports
import cProfile
import psutil
from multiprocessing import Process, Queue

# Third-party libraries
import datetime
import os
from counters import MultiProcessCounters as Counters, BaseCounters
from rate_limiters import MultithreadDequeRateLimiter as DequeRateLimiter
from config import VALID_API_KEYS
from workers import (
    exchange_facing_worker_multithread as exchange_facing_worker, 
    exchange_facing_worker_multithread_test as exchange_facing_worker_test, 
    generate_requests_multithread as generate_requests
)
from utils import log_count_to_file

def main():
    url = "http://127.0.0.1:9999/api/request"
    counters = Counters()
    queue = Queue()

    # Start the request generator process
    request_generator = Process(target=generate_requests, args=(queue,))
    request_generator.start()

    # Start a worker process for each API key
    workers = []
    for api_key in VALID_API_KEYS:
        worker = Process(target=exchange_facing_worker_test, args=(url, api_key, queue, counters))
        worker.start()
        workers.append(worker)

    print('Number of child processes after starting workers:', len(psutil.Process().children(recursive=True)))

    # Wait for all processes to finish
    for worker in workers:
        worker.join()

    request_generator.terminate()

    log_count_to_file(counters)

if __name__ == '__main__':
    profiler = cProfile.Profile()
    profiler.runcall(main)
    profiler.print_stats()
