import zipfile
from pathlib import Path

ENCODINGS = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'gbk', 'shift_jis']

class trich_noi_dung:
    def doc_file(self, duong_dan: Path) -> str:
        for enc in ENCODINGS:
            try:
                return duong_dan.read_text(encoding=enc)
            except (UnicodeDecodeError, UnicodeError):
                continue
        return duong_dan.read_bytes().decode('utf-8', errors='replace')

    def doc_trong_zip(self, duong_dan: Path, ten_file: str) -> str:
        with zipfile.ZipFile(duong_dan, 'r') as zf:
            raw = zf.read(ten_file)
        for enc in ENCODINGS:
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, UnicodeError):
                continue
        return raw.decode('utf-8', errors='replace')
