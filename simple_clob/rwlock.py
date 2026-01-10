"""Read-Write Lock implementation for thread-safe order book."""

import threading
import time
from contextlib import contextmanager
from typing import Optional


class RWLock:
    """
    A Read-Write Lock (RWLock) implementation.

    Allows multiple concurrent readers OR a single writer.
    Uses writer-preference to prevent writer starvation.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._read_ready = threading.Condition(self._lock)
        self._readers = 0
        self._writers_waiting = 0
        self._writer_active = False

    def acquire_read(self, timeout: Optional[float] = None) -> bool:
        """Acquire read lock. Blocks if a writer is active or waiting."""
        with self._lock:
            deadline = None
            if timeout is not None:
                deadline = time.monotonic() + timeout

            while self._writer_active or self._writers_waiting > 0:
                if timeout is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return False
                    if not self._read_ready.wait(timeout=remaining):
                        return False
                else:
                    self._read_ready.wait()

            self._readers += 1
            return True

    def release_read(self):
        """Release read lock."""
        with self._lock:
            self._readers -= 1
            if self._readers == 0:
                self._read_ready.notify_all()

    def acquire_write(self, timeout: Optional[float] = None) -> bool:
        """Acquire write lock. Blocks until all readers and writers release."""
        with self._lock:
            self._writers_waiting += 1
            try:
                deadline = None
                if timeout is not None:
                    deadline = time.monotonic() + timeout

                while self._readers > 0 or self._writer_active:
                    if timeout is not None:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            return False
                        if not self._read_ready.wait(timeout=remaining):
                            return False
                    else:
                        self._read_ready.wait()

                self._writer_active = True
                return True
            finally:
                self._writers_waiting -= 1

    def release_write(self):
        """Release write lock."""
        with self._lock:
            self._writer_active = False
            self._read_ready.notify_all()

    @contextmanager
    def read(self):
        """Context manager for read lock."""
        self.acquire_read()
        try:
            yield
        finally:
            self.release_read()

    @contextmanager
    def write(self):
        """Context manager for write lock."""
        self.acquire_write()
        try:
            yield
        finally:
            self.release_write()
