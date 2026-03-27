from pathlib import Path
from cau_hinh.hang_so import thu_muc_ket_qua

class lap_lai_file:
    def luu_text(self, ten_file: str, noi_dung: str) -> Path:
        duong_dan = Path(thu_muc_ket_qua / ten_file)
        duong_dan.parent.mkdir(parents=True, exist_ok=True)
        duong_dan.write_text(noi_dung, encoding='utf-8')
        return duong_dan
