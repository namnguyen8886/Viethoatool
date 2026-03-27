import json
from pathlib import Path
from cau_hinh.hang_so import thu_muc_tri_nho


class du_lieu_plugin_can_dao:
    def __init__(self, duong_dan: Path | None = None):
        self.duong_dan = duong_dan or (thu_muc_tri_nho / 'plugin_can_dao.json')
        self.duong_dan.parent.mkdir(parents=True, exist_ok=True)
        self.du_lieu = self._tai_du_lieu()

    def _mac_dinh(self) -> dict:
        return {
            'plugin_mac_dinh': [
                'DeluxeMenus', 'MythicHUD', 'MythicMobs', 'ItemsAdder', 'Oraxen',
                'BetterRTP', 'TAB', 'CMI', 'ExcellentCrates', 'ShopGUIPlus'
            ],
            'plugin_can_than': ['ItemsAdder', 'Oraxen'],
            'plugin_bo_qua': ['ProtocolLib', 'Vault', 'ViaVersion', 'PacketEvents'],
            'plugin_nguoi_dung': []
        }

    def _tai_du_lieu(self) -> dict:
        if not self.duong_dan.exists():
            du_lieu = self._mac_dinh()
            self._luu(du_lieu)
            return du_lieu
        try:
            return json.loads(self.duong_dan.read_text(encoding='utf-8'))
        except Exception:
            du_lieu = self._mac_dinh()
            self._luu(du_lieu)
            return du_lieu

    def _luu(self, du_lieu: dict):
        self.duong_dan.write_text(json.dumps(du_lieu, ensure_ascii=False, indent=2), encoding='utf-8')

    def luu(self):
        self._luu(self.du_lieu)

    def tat_ca_plugin_can_dao(self) -> list[str]:
        ds = set(self.du_lieu.get('plugin_mac_dinh', [])) | set(self.du_lieu.get('plugin_nguoi_dung', []))
        return sorted(ds)

    def plugin_bo_qua(self) -> list[str]:
        return list(self.du_lieu.get('plugin_bo_qua', []))

    def them_plugin(self, ten_plugin: str):
        ten_plugin = (ten_plugin or '').strip()
        if not ten_plugin:
            return
        ds = set(self.du_lieu.get('plugin_nguoi_dung', []))
        ds.add(ten_plugin)
        self.du_lieu['plugin_nguoi_dung'] = sorted(ds)
        self.luu()

    def xoa_plugin(self, ten_plugin: str):
        ds = set(self.du_lieu.get('plugin_nguoi_dung', []))
        if ten_plugin in ds:
            ds.remove(ten_plugin)
            self.du_lieu['plugin_nguoi_dung'] = sorted(ds)
            self.luu()
