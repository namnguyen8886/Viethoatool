import json
import hashlib
import re
from pathlib import Path
from typing import Optional
from cau_hinh.hang_so import thu_muc_tri_nho


class bo_nho_dich:
    def __init__(self):
        self.file = Path(thu_muc_tri_nho / 'bo_nho_dich.json')
        if not self.file.exists():
            self.file.write_text('{}', encoding='utf-8')

    def _tai(self) -> dict:
        try:
            raw = json.loads(self.file.read_text(encoding='utf-8'))
        except Exception:
            raw = {}
        if not isinstance(raw, dict):
            return {}
        cleaned = {}
        changed = False
        for k, v in raw.items():
            if not isinstance(v, str):
                changed = True
                continue
            s = self._sanitize(v)
            if not s:
                changed = True
                continue
            cleaned[k] = s
            if s != v:
                changed = True
        if changed:
            self._luu(cleaned)
        return cleaned

    def _luu(self, du_lieu: dict):
        self.file.write_text(json.dumps(du_lieu, ensure_ascii=False, indent=2), encoding='utf-8')

    def _key(self, van_ban: str, lang_from: str, lang_to: str) -> str:
        raw = f'{lang_from}|{lang_to}|{van_ban}'.encode('utf-8')
        return hashlib.sha1(raw).hexdigest()

    def _sanitize(self, text: str) -> str:
        if not text:
            return ''
        text = text.replace('```yaml', '').replace('```yml', '').replace('```json', '').replace('```', '')
        lines = []
        for dong in str(text).splitlines():
            d = dong.strip()
            lower = d.lower()
            if lower.startswith('# translated by ') or lower.startswith('# model:') or lower.startswith('# language:'):
                continue
            lines.append(dong.rstrip())
        text = '\n'.join(lines).strip()
        if re.search(r'__(?:ph|clr|hex)_\d+__|_+(?:ph|clr|hex)_\d+__', text, re.I):
            return ''
        if re.search(r'([&§][0-9a-fk-orA-FK-OR])+\s*_+(?:ph|clr|hex)_\d+__', text):
            return ''
        if len(text) > 20000:
            return ''
        if text.count('menu_title:') > 2 or text.count('items:') > 2 or text.count('click_commands:') > 2:
            return ''
        return text.strip()

    def lay(self, van_ban: str, lang_from: str, lang_to: str) -> Optional[str]:
        du_lieu = self._tai()
        return du_lieu.get(self._key(van_ban, lang_from, lang_to))

    def them(self, van_ban: str, ban_dich: str, lang_from: str, lang_to: str):
        if str(van_ban).strip() == str(ban_dich).strip():
            return
        ban_dich = self._sanitize(ban_dich)
        if not ban_dich:
            return
        du_lieu = self._tai()
        du_lieu[self._key(van_ban, lang_from, lang_to)] = ban_dich
        self._luu(du_lieu)
