from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable


@dataclass
class gg_backend:
    name: str
    base_url: str
    priority: int = 100
    timeout_ms: int = 2500
    max_fail: int = 3
    cooldown_sec: int = 60
    enabled: bool = True
    fail_count: int = 0
    open_until: float = 0.0

    def is_available(self) -> bool:
        return self.enabled and time.time() >= float(self.open_until or 0.0)

    def mark_success(self):
        self.fail_count = 0
        self.open_until = 0.0

    def mark_fail(self):
        self.fail_count += 1
        if self.fail_count >= max(1, int(self.max_fail or 1)):
            self.open_until = time.time() + max(1, int(self.cooldown_sec or 1))
            self.fail_count = 0


class gg_backend_pool:
    def __init__(self, backends: Iterable[gg_backend] | None = None):
        self.backends = sorted(list(backends or []), key=lambda b: (b.priority, b.name))

    @classmethod
    def from_endpoints(
        cls,
        endpoints: list[str],
        timeout_ms: int = 2500,
        max_fail: int = 3,
        cooldown_sec: int = 60,
    ) -> 'gg_backend_pool':
        items = []
        seen = set()
        for idx, raw in enumerate(endpoints or []):
            url = (raw or '').strip()
            if not url or url in seen:
                continue
            seen.add(url)
            name = f'gg_{idx+1}'
            items.append(
                gg_backend(
                    name=name,
                    base_url=url,
                    priority=idx,
                    timeout_ms=timeout_ms,
                    max_fail=max_fail,
                    cooldown_sec=cooldown_sec,
                )
            )
        return cls(items)

    def available(self) -> list[gg_backend]:
        return [b for b in self.backends if b.is_available()]

    def ordered(self) -> list[gg_backend]:
        avail = self.available()
        return avail if avail else [b for b in self.backends if b.enabled]
