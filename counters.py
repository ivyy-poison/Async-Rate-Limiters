import abc
import ctypes
from multiprocessing import Value


class BaseCounters(abc.ABC):
    @abc.abstractmethod
    async def increment_count(self):
        """Increment the counter."""
        pass

    @abc.abstractmethod
    async def get_count(self):
        """Get the current count."""
        pass

    @abc.abstractmethod
    async def get_ignored_count(self):
        """Get the current ignored count."""
        pass

    @abc.abstractmethod
    async def increment_ignored_count(self):
        """Increment the ignored count."""
        pass

    @abc.abstractmethod
    async def get_error_count(self):
        """Get the current error count."""
        pass

    @abc.abstractmethod
    async def increment_error_count(self):
        """Increment the error count."""
        pass

class Counters(BaseCounters):
    def __init__(self):
        self.count = 0
        self.ignored_count = 0
        self.error_count = 0

    def increment_count(self):
        self.count += 1

    def increment_ignored_count(self):
        self.ignored_count += 1

    def increment_error_count(self):
        self.error_count += 1

    def get_count(self):
        return self.count
    
    def get_ignored_count(self):
        return self.ignored_count
    
    def get_error_count(self):
        return self.error_count
    

class MultiProcessCounters(BaseCounters):
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

    def get_count(self):
        return self.count.value
    
    def get_ignored_count(self):
        return self.ignored_count.value
    
    def get_error_count(self):
        return self.error_count.value
    