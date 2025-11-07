import time
import logging
import inspect
import enum
import typing


class TimerResolution(enum.Enum):
    SECONDS = 0
    NANOSECONDS = 1


class Timer:
    def __init__(self, res: TimerResolution = TimerResolution.SECONDS):
        self.log = logging.getLogger(
            f"{self.__class__.__name__}] [{inspect.stack()[1].function}"
        )
        self.log.setLevel(logging.INFO)

        self.res = res
        self.time = time.time if res is TimerResolution.SECONDS else time.time_ns

        self.tic: float | int | None = None
        self.toc: float | int | None = None
        self.running: bool = False

    def is_running(self) -> bool:
        return self.tic != None and self.toc == None

    def reset(self) -> None:
        tic = self.time()

        self.tic = tic
        self.toc = None

    def stop(self) -> None:
        toc = self.time()

        if self.is_running():
            self.toc = toc

    def measure(self) -> float | int | None:
        if not self.tic or not self.toc:
            return None
        return self.toc - self.tic

    def __enter__(self):  # type: ignore
        self.reset()
        return self

    def __exit__(
        self, exc_type: typing.Any, exc: typing.Any, traceback: typing.Any
    ) -> None:
        self.stop()
        self.log.info(
            f"elapsed: {self.measure()}{'s' if self.res is TimerResolution.SECONDS else 'ns'}"
        )
