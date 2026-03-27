import asyncio
import random
import time
from loi.theo_doi_key import trang_thai_key

class quan_ly_key:
    def __init__(self, danh_sach_key: list[str]):
        self.danh_sach = [trang_thai_key(key=k) for k in danh_sach_key if k and k.strip()]
        self.khoa = asyncio.Lock()

    def _dung_duoc(self, item: trang_thai_key) -> bool:
        now = time.time()
        return now >= item.cooldown_until and now >= item.ban_until and item.status != 'invalid'

    async def chon_key(self) -> str:
        async with self.khoa:
            danh_sach = [x for x in self.danh_sach if self._dung_duoc(x)]
            if not danh_sach:
                raise RuntimeError('khong_con_key_song')
            danh_sach.sort(key=lambda x: x.last_used_at)
            item = danh_sach[0]
            item.last_used_at = time.time()
            item.status = 'active'
            return item.key

    async def danh_dau_429(self, key: str):
        await asyncio.sleep(random.uniform(1, 2))
        async with self.khoa:
            for item in self.danh_sach:
                if item.key == key:
                    item.quota_fail_count += 1
                    item.cooldown_until = time.time() + 300
                    item.status = 'cooldown'
                    item.reason = 'rate_limit'
                    if item.quota_fail_count >= 3:
                        item.ban_until = time.time() + 86400
                        item.status = 'banned_1d'
                    return

    async def danh_dau_invalid(self, key: str):
        async with self.khoa:
            for item in self.danh_sach:
                if item.key == key:
                    item.status = 'invalid'
                    item.reason = 'invalid'
                    return

    def thong_ke(self) -> list[dict]:
        return [item.__dict__.copy() for item in self.danh_sach]
