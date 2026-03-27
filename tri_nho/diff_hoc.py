import json
import re
from pathlib import Path
from cau_hinh.hang_so import thu_muc_tri_nho


class diff_hoc:
    def __init__(self):
        self.file = Path(thu_muc_tri_nho / 'diff_hoc.json')
        if not self.file.exists():
            self.file.write_text(json.dumps({'term': {}, 'pattern': {}}, ensure_ascii=False, indent=2), encoding='utf-8')

    def _tai(self):
        try:
            data = json.loads(self.file.read_text(encoding='utf-8'))
        except Exception:
            data = {'term': {}, 'pattern': {}}
        if not isinstance(data, dict):
            data = {'term': {}, 'pattern': {}}
        data.setdefault('term', {})
        data.setdefault('pattern', {})
        return data

    def _luu(self, du_lieu):
        self.file.write_text(json.dumps(du_lieu, ensure_ascii=False, indent=2), encoding='utf-8')

    def _hop_le_de_hoc(self, goc: str, dich: str) -> bool:
        goc = str(goc or '').strip()
        dich = str(dich or '').strip()
        if not goc or not dich:
            return False
        if len(goc) > 1200 or len(dich) > 1200:
            return False
        if re.search(r'__(?:ph|clr|hex)_\d+__|_+(?:ph|clr|hex)_\d+__', goc + '\n' + dich, re.I):
            return False
        if '\n' in goc or '\n' in dich:
            if len(goc.splitlines()) > 8 or len(dich.splitlines()) > 8:
                return False
        block_keys = ('menu_title:', 'items:', 'click_commands:', 'left_click_commands:', 'right_click_commands:', 'view_requirement:')
        if any(k in goc for k in block_keys):
            return False
        if any(k in dich for k in block_keys):
            return False
        if '# Translated by ' in dich or '# Model:' in dich or '# Language:' in dich:
            return False
        return True

    def hoc_tu_cap(self, goc: str, dich: str):
        if not self._hop_le_de_hoc(goc, dich):
            return
        du_lieu = self._tai()
        if goc == dich:
            du_lieu['term'][goc] = {'hanh_dong': 'giu_nguyen', 'hits': du_lieu['term'].get(goc, {}).get('hits', 0) + 1}
        else:
            du_lieu['term'][goc] = {'hanh_dong': 'da_dich', 'ban_dich': dich, 'hits': du_lieu['term'].get(goc, {}).get('hits', 0) + 1}
        self._luu(du_lieu)

    def lay_goi_y(self, goc: str):
        return self._tai().get('term', {}).get(goc)
