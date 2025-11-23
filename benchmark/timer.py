import time


class CodeTimer:
    def __init__(self, name=None):
        self.name = name
        self.t_start = None
        self.elapsed = None

    def __enter__(self):
        self.t_start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self.t_start
