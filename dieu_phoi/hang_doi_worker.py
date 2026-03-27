import asyncio

class hang_doi_worker:
    def __init__(self, so_luong: int = 3):
        self.queue = asyncio.Queue()
        self.so_luong = so_luong
        self.nhiem_vu = []

    async def them(self, item):
        await self.queue.put(item)

    async def dung(self):
        while not self.queue.empty():
            await asyncio.sleep(0.05)
