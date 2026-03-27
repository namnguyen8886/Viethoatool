import zipfile
from pathlib import Path
from cau_hinh.hang_so import thu_muc_ket_qua

class dong_goi:
    def zip_thu_muc(self, ma_job: str, danh_sach_file: list[Path]) -> Path:
        file_zip = Path(thu_muc_ket_qua / f'{ma_job}.zip')
        with zipfile.ZipFile(file_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for duong_dan in danh_sach_file:
                zf.write(duong_dan, arcname=duong_dan.name)
        return file_zip
