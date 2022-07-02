"""Wrapper for `requests` library."""
import time

from requests import Session


class ThrottledSession(Session):
    """HTTP session with delay between requests."""

    interval: float
    first_request_performed: bool

    def __init__(self, interval: float):
        """Initialize."""
        super().__init__()
        self.interval = interval
        self.first_request_performed = False

    def request(self, method, url, **kwargs):
        """Perform HTTP request."""
        if self.first_request_performed:
            if self.interval > 0.0:
                time.sleep(self.interval)
        else:
            self.first_request_performed = True
        return super().request(method, url, **kwargs)
