import time
import logging
import inspect
import enum


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

        self.tic = None
        self.toc = None
        self.running = False

    def is_running(self):
        return self.tic != None and self.toc == None

    def reset(self) -> None:
        tic = self.time()

        self.tic = tic
        self.toc = None

    def stop(self) -> None:
        toc = self.time()

        if self.is_running():
            self.toc = toc

    def measure(self):
        if not self.tic or not self.toc:
            return None
        return self.toc - self.tic

    def __enter__(self):
        self.reset()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.stop()
        self.log.info(
            f"elapsed: {self.measure()}{'s' if self.res is TimerResolution.SECONDS else 'ns'}"
        )
