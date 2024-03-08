import ctypes
from multiprocessing import Value

class Counters:
    def __init__(self):
        self.count = Value(ctypes.c_int, 0)
        self.ignored_count = Value(ctypes.c_int, 0)
        self.error_count = Value(ctypes.c_int, 0)

    def increment_count(self):
        with self.count.get_lock():
            self.count.value += 1

    def increment_ignored_count(self):
        with self.ignored_count.get_lock():
            self.ignored_count.value += 1

    def increment_error_count(self):
        with self.error_count.get_lock():
            self.error_count.value += 1