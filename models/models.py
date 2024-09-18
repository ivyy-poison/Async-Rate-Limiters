import time
from utils import timestamp_ms

class RateLimiterTimeout(Exception):
    pass
class Request:
    def __init__(self, req_id):
        self.req_id = req_id
        self.create_time = timestamp_ms()
