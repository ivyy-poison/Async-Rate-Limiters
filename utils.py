import time
from datetime import datetime
from counters import BaseCounters
import os

def timestamp_ms() -> int:
    return int(time.time() * 1000)

def log_count_to_file(counters: BaseCounters):
    if os.path.exists("output.txt"):
        with open("output.txt", "r") as f:
            content = f.read()
    else:
        content = ""

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count, ignored_count, error_count = counters.get_count(), counters.get_ignored_count(), counters.get_error_count()

    # Write the current time and count to the top of the file
    with open("output.txt", "w") as f:
        f.write(f"Current time: {current_time}, Successful requests: {count}, Ignored requests: {ignored_count}, 429 errors: {error_count}\n{content}")
