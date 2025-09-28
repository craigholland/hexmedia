from __future__ import annotations

import logging
import time
import threading
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, Generator, Generic, Iterable, List, Optional, Tuple, TypeVar

T = TypeVar("T")
R = TypeVar("R")

log = logging.getLogger(__name__)


@dataclass
class ThreadStats:
    start_ts: float
    tasks_submitted: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0

    @property
    def uptime_sec(self) -> float:
        return time.time() - self.start_ts

    @property
    def in_flight(self) -> int:
        return max(0, self.tasks_submitted - (self.tasks_completed + self.tasks_failed))


class ThreadManager(Generic[T, R]):
    """
    A reusable, bounded thread-pool manager focused on I/O-bound workloads.

    Features
    --------
    - submit(fn, *args, **kwargs) -> Future
    - imap_unordered(fn, iterable, prefetch=None) -> yields results as they finish
    - map(fn, iterable, preserve_order=True) -> List[R]
    - Bounded outstanding tasks via a semaphore (max_queue)
    - Stop event accessible by tasks (optional)
    - Stats snapshot
    - Clean shutdown, context manager support

    Notes
    -----
    - For CPU-bound work, prefer multiprocessing. This is tuned for I/O-bound tasks (hashing, ffprobe).
    """

    def __init__(
        self,
        name: str = "worker",
        max_workers: Optional[int] = None,
        max_queue: Optional[int] = None,
        thread_name_prefix: Optional[str] = None,
        log_exceptions: bool = True,
    ) -> None:
        """
        Parameters
        ----------
        name:
            Logical name for metrics/logging.
        max_workers:
            Max threads in the pool. Default: auto for I/O (~min(8, max(4, 2*CPUs))).
        max_queue:
            Max number of *outstanding* tasks (submitted but not finished).
            If None or <= 0, it's effectively unbounded (not recommended for very large workloads).
        thread_name_prefix:
            Prefix for thread names.
        log_exceptions:
            If True, exceptions in tasks are logged when futures complete.
        """
        if max_workers is None:
            import os
            n = os.cpu_count() or 4
            max_workers = max(4, min(8, n * 2))  # I/O-friendly default

        self._name = name
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix or f"{name}",
        )
        self._stop = threading.Event()
        self._stats = ThreadStats(start_ts=time.time())
        self._log_exceptions = log_exceptions

        # Bounded outstanding-tasks controller
        if not max_queue or max_queue <= 0:
            self._slots = None  # unbounded
        else:
            # slots = how many tasks can be outstanding at once
            self._slots = threading.Semaphore(max_queue)

        self._closed = False
        self._lock = threading.Lock()

    # -------------------------
    # Lifecycle
    # -------------------------
    def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
        """Shut down the executor. Safe to call multiple times."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._stop.set()
        self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)

    def __enter__(self) -> "ThreadManager[T, R]":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.shutdown(wait=True, cancel_futures=True)

    @property
    def stop_event(self) -> threading.Event:
        """A cooperative stop flag your tasks can check if you support cancellation."""
        return self._stop

    def stats(self) -> ThreadStats:
        """Return a *snapshot* of current stats."""
        with self._lock:
            return ThreadStats(
                start_ts=self._stats.start_ts,
                tasks_submitted=self._stats.tasks_submitted,
                tasks_completed=self._stats.tasks_completed,
                tasks_failed=self._stats.tasks_failed,
            )

    # -------------------------
    # Submission
    # -------------------------
    def submit(self, fn: Callable[..., R], /, *args, **kwargs) -> Future[R]:
        """
        Submit a single callable. Applies queue bounding and exception logging.
        Returns a Future that will hold the result or exception.
        """
        if self._closed:
            raise RuntimeError(f"{self._name}: submit() after shutdown")

        # Apply backpressure if bounded
        if self._slots is not None:
            self._slots.acquire()

        def _wrapped(*a, **kw) -> R:
            try:
                return fn(*a, **kw)
            finally:
                # release slot when the callable *finishes*, success or error
                if self._slots is not None:
                    self._slots.release()

        with self._lock:
            self._stats.tasks_submitted += 1

        fut: Future[R] = self._executor.submit(_wrapped, *args, **kwargs)

        if self._log_exceptions:
            def _cb(f: Future[R]) -> None:
                try:
                    _ = f.result()
                    with self._lock:
                        self._stats.tasks_completed += 1
                except Exception as e:
                    with self._lock:
                        self._stats.tasks_failed += 1
                    log.exception("%s task failed: %s", self._name, e)

            fut.add_done_callback(_cb)
        else:
            def _cb2(f: Future[R]) -> None:
                try:
                    _ = f.result()
                    with self._lock:
                        self._stats.tasks_completed += 1
                except Exception:
                    with self._lock:
                        self._stats.tasks_failed += 1

            fut.add_done_callback(_cb2)

        return fut

    # -------------------------
    # Bulk helpers
    # -------------------------
    def imap_unordered(
        self,
        fn: Callable[[T], R],
        iterable: Iterable[T],
        *,
        prefetch: Optional[int] = None,
    ) -> Generator[R, None, None]:
        """
        Submit items from 'iterable' and yield results as they complete (unordered).
        'prefetch' controls how many tasks we keep in flight in addition to max_workers.
        If bounded by max_queue, that also applies.

        This is great for big inputs without materializing all futures at once.
        """
        if self._closed:
            raise RuntimeError(f"{self._name}: imap_unordered() after shutdown")

        # Calculate how many to keep inflight
        # If queue is unbounded, use a modest default prefetch (2x workers)
        # If bounded, we'll respect the semaphore anyway.
        workers = getattr(self._executor, "_max_workers", 4)
        if prefetch is None:
            prefetch = workers * 2

        inflight: List[Future[R]] = []
        it = iter(iterable)

        # Prime the pump
        def _fill() -> None:
            while len(inflight) < (workers + prefetch):
                try:
                    item = next(it)
                except StopIteration:
                    break
                inflight.append(self.submit(fn, item))

        _fill()
        while inflight:
            for done in as_completed(inflight, timeout=None):
                inflight.remove(done)
                # Pass through the result/raise; caller decides how to handle
                yield done.result()
                _fill()

    def map(
        self,
        fn: Callable[[T], R],
        iterable: Iterable[T],
        *,
        preserve_order: bool = True,
    ) -> List[R]:
        """
        Convenience wrapper: returns a list of results.
        If preserve_order=False, uses imap_unordered for speed / lower memory.
        """
        if preserve_order:
            # Submit all (bounded by max_queue if set), then block for results in order
            futures_list = [self.submit(fn, item) for item in iterable]
            return [f.result() for f in futures_list]
        else:
            return list(self.imap_unordered(fn, iterable))
