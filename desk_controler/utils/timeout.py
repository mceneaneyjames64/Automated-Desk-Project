import signal
from contextlib import contextmanager


class TimeoutError(Exception):
    """Custom timeout exception"""
    pass


@contextmanager
def timeout(seconds, error_message="Operation timed out"):
    """Context manager for timeout handling using signals"""
    def timeout_handler(signum, frame):
        raise TimeoutError(error_message)
    
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(int(seconds))
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
