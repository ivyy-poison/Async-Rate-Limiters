import abc

class BaseRateLimiter(abc.ABC):
    @abc.abstractmethod
    async def acquire(self):
        """Asynchronously acquire access, respecting the rate limit."""
        yield