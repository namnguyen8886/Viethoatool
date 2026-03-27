import random

class tinh_backoff:
    def __init__(self, base: float = 2.0, max_time: float = 60.0):
        self.base = base
        self.max_time = max_time

    def tinh(self, lan_thu: int) -> float:
        cho = min(self.base ** lan_thu, self.max_time)
        jitter = random.uniform(0, cho * 0.1)
        return cho + jitter
