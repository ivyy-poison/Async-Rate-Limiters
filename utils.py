import time
from datetime import datetime
import os

# region: DO NOT CHANGE - the code within this region can be assumed to be "correct"

def timestamp_ms() -> int:
    return int(time.time() * 1000)

# endregion

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

def log_count_to_file_multithread(counters):
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