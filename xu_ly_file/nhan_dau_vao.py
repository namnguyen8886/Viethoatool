from pathlib import Path
import aiohttp
from cau_hinh.hang_so import thu_muc_tam

class nhan_dau_vao:
    async def tai_tu_link(self, url: str, ten_file: str | None = None) -> Path:
        ten_file = ten_file or url.split('/')[-1] or 'tai_xuong.tmp'
        duong_dan = Path(thu_muc_tam / ten_file)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                duong_dan.write_bytes(await resp.read())
        return duong_dan

    def nhan_file_san(self, duong_dan: str) -> Path:
        return Path(duong_dan)
