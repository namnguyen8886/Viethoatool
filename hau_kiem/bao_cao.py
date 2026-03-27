import json
from pathlib import Path
from cau_hinh.hang_so import thu_muc_bao_cao

class bao_cao:
    def luu(self, ma_job: str, du_lieu: dict) -> Path:
        duong_dan = Path(thu_muc_bao_cao / f'{ma_job}.json')
        duong_dan.write_text(json.dumps(du_lieu, ensure_ascii=False, indent=2), encoding='utf-8')
        return duong_dan
