import zipfile
from pathlib import Path
from xu_ly_file.phan_loai_file import phan_loai_file
from tri_nho.du_lieu_plugin_can_dao import du_lieu_plugin_can_dao


class quet_folder_ngoai:
    def __init__(self):
        self.phan_loai = phan_loai_file()
        self.du_lieu = du_lieu_plugin_can_dao()

    def _tach_folder(self, ten: str) -> list[str]:
        return [x for x in ten.replace('\\', '/').split('/') if x]

    def _folder_ung_vien_tu_zip(self, duong_dan: Path) -> dict[str, dict]:
        ket_qua: dict[str, dict] = {}
        with zipfile.ZipFile(duong_dan, 'r') as zf:
            for ten in zf.namelist():
                if ten.endswith('/'):
                    continue
                phan = self._tach_folder(ten)
                if len(phan) < 2:
                    continue
                for i in range(min(3, len(phan) - 1)):
                    path_folder = '/'.join(phan[: i + 1])
                    ten_folder = phan[i]
                    muc = ket_qua.setdefault(path_folder, {
                        'ten': ten_folder,
                        'path': path_folder,
                        'so_file_hop_le': 0,
                        'tong_file': 0,
                        'goi_y': 'xem_them',
                        'diem': 0,
                    })
                    muc['tong_file'] += 1
                    if self.phan_loai.ho_tro_khong(ten):
                        muc['so_file_hop_le'] += 1
        return ket_qua

    def _goi_y(self, ten: str, path: str, so_file_hop_le: int) -> tuple[str, int]:
        ten_thuong = ten.lower()
        path_thuong = path.lower()
        diem = 0
        goi_y = 'xem_them'
        if ten in self.du_lieu.tat_ca_plugin_can_dao() or any(x.lower() in path_thuong for x in [p.lower() for p in self.du_lieu.tat_ca_plugin_can_dao()]):
            diem += 80
            goi_y = 'nen_dao'
        if ten in self.du_lieu.plugin_bo_qua():
            diem -= 90
            goi_y = 'bo_qua'
        if ten_thuong in {'plugins', 'addons', 'itemsadder', 'oraxen', 'mythichud', 'mythicmobs'}:
            diem += 25
        if so_file_hop_le >= 3:
            diem += 20
        if any(x in ten_thuong for x in ['assets', 'textures', 'models', 'font', 'resource_pack']):
            diem -= 50
            if goi_y != 'nen_dao':
                goi_y = 'bo_qua'
        if diem >= 50 and goi_y != 'bo_qua':
            goi_y = 'nen_dao'
        elif 15 <= diem < 50 and goi_y != 'bo_qua':
            goi_y = 'can_than'
        return goi_y, diem

    def quet(self, duong_dan: Path) -> dict:
        muc = []
        if duong_dan.suffix.lower() == '.zip':
            du_lieu = self._folder_ung_vien_tu_zip(duong_dan)
            for item in du_lieu.values():
                goi_y, diem = self._goi_y(item['ten'], item['path'], item['so_file_hop_le'])
                item['goi_y'] = goi_y
                item['diem'] = diem
                if item['so_file_hop_le'] > 0 or goi_y != 'xem_them':
                    muc.append(item)
        else:
            for child in sorted([x for x in duong_dan.iterdir() if x.is_dir()]):
                goi_y, diem = self._goi_y(child.name, child.name, 0)
                muc.append({
                    'ten': child.name,
                    'path': child.name,
                    'so_file_hop_le': 0,
                    'tong_file': 0,
                    'goi_y': goi_y,
                    'diem': diem,
                })
        muc.sort(key=lambda x: (-x['diem'], x['path']))
        for i, item in enumerate(muc, start=1):
            item['id'] = i
        return {'tong_folder': len(muc), 'muc': muc}
