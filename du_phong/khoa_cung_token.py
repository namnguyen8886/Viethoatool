import re
from dataclasses import dataclass

@dataclass
class ket_qua_khoa:
    noi_dung: str
    bang_anh_xa: dict

class khoa_cung_token:
    mau = [
        r'%[^%\s]+%',
        r'\{\{[^}]+\}\}',
        r'\{\d+\}',
        r'&[0-9a-fk-or]',
        r'§[0-9a-fk-or]',
        r'&#[A-Fa-f0-9]{6}',
        r'/[A-Za-z0-9_:\-]+',
        r'https?://\S+',
        r'[A-Za-z0-9_]+\.[A-Za-z0-9_.-]+',
    ]

    def khoa(self, noi_dung: str) -> ket_qua_khoa:
        bang = {}
        dem = 0
        for mau in self.mau:
            for kq in list(re.finditer(mau, noi_dung)):
                gia_tri = kq.group(0)
                if gia_tri in bang.values():
                    continue
                token = f'__khoa_{dem}__'
                noi_dung = noi_dung.replace(gia_tri, token)
                bang[token] = gia_tri
                dem += 1
        return ket_qua_khoa(noi_dung=noi_dung, bang_anh_xa=bang)

    def mo(self, noi_dung: str, bang_anh_xa: dict) -> str:
        for token, gia_tri in bang_anh_xa.items():
            noi_dung = noi_dung.replace(token, gia_tri)
        return noi_dung
