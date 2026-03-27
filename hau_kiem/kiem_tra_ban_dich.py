from __future__ import annotations

import re
from collections import Counter

try:
    import yaml
except Exception:
    yaml = None


class kiem_tra_ban_dich:
    def __init__(self):
        self._patterns = {
            'placeholder_phan_tram': r'%[^%\s]+%',
            'placeholder_so': r'\{\d+\}',
            'placeholder_ngoac': r'\{[A-Za-z_][A-Za-z0-9_.-]*\}',
            'placeholder_nhon': r'<[A-Za-z_][A-Za-z0-9_./:-]*>',
            'mau_amp': r'&[0-9a-fk-orA-FK-OR]',
            'mau_section': r'§[0-9a-fk-orA-FK-OR]',
            'mau_hex': r'&#[A-Fa-f0-9]{6}',
            'token_noi_bo': r'__(?:ph|hex|clr)_\d+__|_+(?:ph|hex|clr)_\d+__|@@TOK_\d{1,6}@@',
        }
        self._re_token_internal = re.compile(self._patterns['token_noi_bo'], re.I)
        self._re_token_internal_strict = re.compile(r'__(?:ph|hex|clr)_\d+__|@@TOK_\d{1,6}@@', re.I)

    def _dem(self, pat: str, text: str) -> Counter:
        return Counter(re.findall(pat, text or ''))

    def _kiem_tra_lech_token(self, goc: str, dich: str, loi: list[str]):
        for ten, pat in self._patterns.items():
            if ten == 'token_noi_bo':
                continue
            if self._dem(pat, goc) != self._dem(pat, dich):
                loi.append(f'lech_{ten}')

    def _flatten_yaml(self, obj, prefix=''):
        out = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = f"{prefix}.{k}" if prefix else str(k)
                out.append((key, 'dict_key'))
                out.extend(self._flatten_yaml(v, key))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                key = f"{prefix}[{i}]"
                out.append((key, 'list_item'))
                out.extend(self._flatten_yaml(v, key))
        else:
            kind = type(obj).__name__ if obj is not None else 'null'
            out.append((prefix, kind))
        return out

    def _co_dang_yaml(self, text: str) -> bool:
        text = text or ''
        return ':' in text and '\n' in text

    def _kiem_tra_yaml_cau_truc(self, goc: str, dich: str, loi: list[str]):
        if yaml is None or not self._co_dang_yaml(goc):
            return
        try:
            g = yaml.safe_load(goc)
        except Exception:
            return
        try:
            d = yaml.safe_load(dich)
        except Exception:
            loi.append('yaml_khong_parse_duoc')
            return
        if g is None or d is None:
            return
        fg = Counter(self._flatten_yaml(g))
        fd = Counter(self._flatten_yaml(d))
        if fg != fd:
            loi.append('lech_cau_truc_yaml')

    def kiem_tra(self, goc: str, dich: str) -> dict:
        loi: list[str] = []
        goc = goc or ''
        dich = dich or ''

        if not dich.strip():
            loi.append('rong')
        if self._re_token_internal.search(dich):
            loi.append('con_token_noi_bo')

        self._kiem_tra_lech_token(goc, dich, loi)
        self._kiem_tra_yaml_cau_truc(goc, dich, loi)

        return {
            'hop_le': not loi,
            'loi': loi,
            'co_token_noi_bo': bool(self._re_token_internal_strict.search(dich)),
            'so_dong_goc': len(goc.splitlines()) if goc else 0,
            'so_dong_dich': len(dich.splitlines()) if dich else 0,
        }
