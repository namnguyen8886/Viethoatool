from __future__ import annotations

import asyncio


class bo_dieu_toc_gg:
    def __init__(self, requests_per_second: float = 1.6, min_concurrency: int = 2, max_concurrency: int = 6):
        self.requests_per_second = max(float(requests_per_second or 1.0), 0.1)
        self._min_interval = 1.0 / self.requests_per_second
        self._rate_lock = asyncio.Lock()
        self._last = 0.0

        self.min_concurrency = max(1, int(min_concurrency or 1))
        self.max_concurrency = max(self.min_concurrency, int(max_concurrency or self.min_concurrency))
        self.current_concurrency = self.min_concurrency
        self._active = 0
        self._cond = asyncio.Condition()
        self._success_streak = 0
        self._failure_streak = 0

    async def cho_luot(self):
        loop = asyncio.get_running_loop()
        async with self._rate_lock:
            now = loop.time()
            wait = self._min_interval - (now - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
                now = loop.time()
            self._last = now

    async def vao_backend(self):
        async with self._cond:
            while self._active >= self.current_concurrency:
                await self._cond.wait()
            self._active += 1

    async def ra_backend(self):
        async with self._cond:
            self._active = max(0, self._active - 1)
            self._cond.notify_all()

    async def bao_thanh_cong(self):
        async with self._cond:
            self._success_streak += 1
            self._failure_streak = 0
            if self.current_concurrency < self.max_concurrency and self._success_streak >= max(3, self.current_concurrency):
                self.current_concurrency += 1
                self._success_streak = 0
                self._cond.notify_all()

    async def bao_that_bai_tam_thoi(self):
        async with self._cond:
            self._failure_streak += 1
            self._success_streak = 0
            if self.current_concurrency > self.min_concurrency:
                giam = 2 if self._failure_streak >= 3 else 1
                self.current_concurrency = max(self.min_concurrency, self.current_concurrency - giam)
            self._cond.notify_all()
