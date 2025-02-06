# ---------------------------------------------------------------------------- #

import threading
import functools
import logging
import asyncio
from queue import Queue
from typing import Any, Callable, Dict

# ---------------------------------------------------------------------------- #


class Worker(threading.Thread):
    """
    A wrapper for the Thread class.
    """
    logger: logging.Logger
    _handlers: dict[str, Callable]
    _queue: Queue
    _target: Callable

    def __init__(
        self,
        name: str,
        target: Callable
    ) -> None:
        """
        Initializes the worker.
        """
        self.logger = logging.getLogger('mrkr.worker')

        self._queue = Queue()
        super().__init__(target=target, name=name, daemon=True)

        self.stop_event = threading.Event()

        self.start()

        self.logger.debug(f"Worker '{self.name}' initialized.")

    def put(self, *args: Any, **kwargs: Any) -> None:
        """
        Put a new process in the worker's queue.
        """
        self._queue.put({"args": args, "kwargs": kwargs})

    def run(
        self
    ) -> None:
        """
        Run the worker.
        """
        while not self.stop_event.is_set():
            params = self._queue.get()

            self.logger.debug(
                f"Worker {self.name} activated."
            )

            try:
                asyncio.run(
                    self._target(*params["args"], **params["kwargs"])
                )
            except Exception as exception:
                self.logger.exception(exception)
                self.logger.debug(f"Worker {self.name} is abandoning task "
                                  f"due to an exception.")

            self._queue.task_done()

    def stop(self) -> None:
        """
        Stop the worker.
        """
        self.stop_event.set()

        self._queue.put(None)

    def join(self, timeout: float | None = None) -> None:
        """
        Wait till all processes have finished.
        """
        self._queue.join()

        super().join(timeout=timeout)

# ---------------------------------------------------------------------------- #


class WorkerManager():
    """
    A worker manager that starts background threads and assigns processes from
    a queue to them.
    """
    logger: logging.Logger

    _workers: Dict[str, Worker]

    def __init__(self) -> None:
        """
        Initializes the worker manager.
        """
        self.logger = logging.getLogger('mrkr.worker')

        self._workers = {}

    def _add_worker(self, alias: str, method: Callable) -> None:
        if alias in self._workers:
            raise Exception(f"Worker '{alias}' already exists.")

        self._workers[alias] = Worker(target=method, name=alias)

    def workermethod(
        self,
        alias: str
    ) -> Callable:
        """
        Creates a decorator for a worker method.
        """
        def decorator(
            func: Callable
        ) -> None:
            @functools.wraps(func)
            def wrapper(
                *args: Any,
                **kwargs: Any
            ) -> Any:
                result = func(*args, **kwargs)
                return result

            self._add_worker(alias=alias, method=wrapper)

        return decorator

    def put(
        self,
        name: str,
        *args: Any,
        **kwargs: Any
    ) -> None:
        """
        Puts a new task in the worker manager's queue.
        """
        if name not in self._workers:
            raise Exception(f"Unknown worker '{name}'.")

        worker = self._workers[name]
        worker.put(*args, **kwargs)

    def join(self) -> None:
        """
        Wait till all process have finished.
        """
        for worker in self._workers.values():
            worker.join()


# ---------------------------------------------------------------------------- #
