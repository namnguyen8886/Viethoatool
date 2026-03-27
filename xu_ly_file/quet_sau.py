import zipfile
from pathlib import Path
from xu_ly_file.phan_loai_file import phan_loai_file
from tri_nho.du_lieu_plugin_can_dao import du_lieu_plugin_can_dao


class quet_sau:
    def __init__(self):
        self.phan_loai = phan_loai_file()
        self.du_lieu = du_lieu_plugin_can_dao()

    def _lay_plugin_da_chon(self, ds_plugin_can_dao: list[str] | None) -> list[str]:
        if ds_plugin_can_dao is None:
            return []
        return [x.replace('\\', '/').strip('/') for x in ds_plugin_can_dao if x]

    def _thuoc_plugin(self, ten: str, ds_plugin: list[str]) -> bool:
        ten = ten.replace('\\', '/').strip('/')
        phan = ten.split('/')
        for plugin in ds_plugin:
            plugin_clean = plugin.replace('\\', '/').strip('/')
            if plugin_clean in ten:
                return True
            basename = plugin_clean.split('/')[-1].lower()
            if basename in [p.lower() for p in phan[:4]]:
                return True
        return False

    def quet(self, duong_dan: Path, ds_plugin_can_dao: list[str] | None = None) -> dict:
        ds_plugin = self._lay_plugin_da_chon(ds_plugin_can_dao)
        kq = {
            'tong': 0,
            'can_dich': [],
            'bo_qua': [],
            'archive': False,
            'plugin_duoc_dao': ds_plugin,
            'bo_loc_plugin': bool(ds_plugin),
        }
        if duong_dan.suffix.lower() == '.zip':
            kq['archive'] = True
            with zipfile.ZipFile(duong_dan, 'r') as zf:
                for ten in zf.namelist():
                    if ten.endswith('/'):
                        continue
                    if ds_plugin and not self._thuoc_plugin(ten, ds_plugin):
                        kq['bo_qua'].append(ten)
                        continue
                    kq['tong'] += 1
                    if self.phan_loai.ho_tro_khong(ten):
                        kq['can_dich'].append(ten)
                    else:
                        kq['bo_qua'].append(ten)
        else:
            if duong_dan.is_dir():
                for tep in duong_dan.rglob('*'):
                    if not tep.is_file():
                        continue
                    rel = tep.relative_to(duong_dan).as_posix()
                    if ds_plugin and not self._thuoc_plugin(rel, ds_plugin):
                        kq['bo_qua'].append(rel)
                        continue
                    kq['tong'] += 1
                    if self.phan_loai.ho_tro_khong(rel):
                        kq['can_dich'].append(rel)
                    else:
                        kq['bo_qua'].append(rel)
            else:
                kq['tong'] = 1
                if self.phan_loai.ho_tro_khong(duong_dan.name):
                    kq['can_dich'].append(duong_dan.name)
                else:
                    kq['bo_qua'].append(duong_dan.name)
        return kq
