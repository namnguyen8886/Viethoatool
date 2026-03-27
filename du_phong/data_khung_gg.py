from __future__ import annotations

import json
import re
from pathlib import Path

try:
    import yaml
except Exception:
    yaml = None


class data_khung_gg:
    def __init__(self, thu_muc_goc: str | Path | None = None):
        self.thu_muc_goc = Path(thu_muc_goc or Path(__file__).resolve().parents[1] / 'du_lieu_gg')
        self.file_common = self.thu_muc_goc / 'chung' / 'common_plugin_keys_shield.yml'
        self.file_diff = Path(__file__).resolve().parents[1] / 'du_lieu' / 'tri_nho' / 'diff_hoc.json'
        self.du_lieu = {}
        self._da_nap = False
        self.default_key_dich = {
            'displayname', 'display_name', 'name', 'title', 'subtitle', 'description', 'message',
            'messages', 'text', 'content', 'status', 'available', 'lore', 'menu_title', 'menu_subtitle',
            'header', 'footer', 'lines'
        }
        self.default_key_cam = {
            'permission', 'permissions', 'material', 'slot', 'slots', 'priority', 'amount', 'size', 'type',
            'cooldown', 'command', 'commands', 'open_command', 'open_commands', 'console_commands', 'player_commands',
            'requirements', 'view_requirement', 'input', 'output', 'sound', 'item', 'page', 'row',
            'basehead', 'texture', 'modeldata', 'model_data', 'register_command', 'item_flags'
        }
        self.default_list_dich = {'lore', 'description', 'messages', 'text', 'lines'}
        self.default_list_cam = {'commands'}

    def tao_mau_neu_thieu(self):
        chung = self.thu_muc_goc / 'chung'
        chung.mkdir(parents=True, exist_ok=True)
        if not self.file_common.exists():
            self.file_common.write_text(
                """key_dich_mac_dinh:
  - display_name
  - name
  - title
  - subtitle
  - menu_title
  - lore
  - lines
key_cam_mac_dinh:
  - command
  - commands
  - material
  - slot
list_dich_theo_cha:
  - lore
  - messages
  - lines
list_cam_theo_cha:
  - commands
placeholder_patterns:
  - "%[^%]+%"
  - "\\{[^{}]+\\}"
color_hex_patterns:
  - "&#[0-9a-fA-F]{6}"
  - "#[0-9a-fA-F]{6}"
color_code_patterns:
  - "&[0-9a-fA-F]"
format_code_patterns:
  - "&[k-orK-OR]"
""",
                encoding='utf-8',
            )

    def nap(self, force: bool = False):
        if self._da_nap and not force:
            return self.thong_ke()
        self.tao_mau_neu_thieu()
        self.du_lieu = {
            'key_dich': set(self.default_key_dich),
            'key_cam': set(self.default_key_cam),
            'list_dich_theo_cha': set(self.default_list_dich),
            'list_cam_theo_cha': set(self.default_list_cam),
            'placeholder': [r'%[^%]+%', r'\{[^{}]+\}'],
            'mau_hex': [r'&#[0-9a-fA-F]{6}', r'<#[0-9a-fA-F]{6}>', r'\{#[0-9a-fA-F]{6}\}', r'#[0-9a-fA-F]{6}'],
            'mau_thuong': [r'&[0-9a-fA-F]', r'§[0-9a-fA-F]'],
            'dinh_dang': [r'&[k-orK-OR]', r'§[k-orK-OR]'],
            'khung_dich': [],
            'khung_cam': [],
            'hoc_pattern': {'key_dich': {}, 'key_cam': {}, 'list_dich_theo_cha': {}, 'list_cam_theo_cha': {}},
        }
        self._nap_common_file()
        self._nap_folder_rules()
        self._nap_diff_hoc_pattern()
        for k in ('placeholder', 'mau_hex', 'mau_thuong', 'dinh_dang'):
            self.du_lieu[k] = self._unique(self.du_lieu[k])
        self._da_nap = True
        return self.thong_ke()

    def thong_ke(self):
        return {
            'thu_muc': str(self.thu_muc_goc),
            'key_dich': len(self.du_lieu.get('key_dich', [])),
            'key_cam': len(self.du_lieu.get('key_cam', [])),
            'list_dich_theo_cha': len(self.du_lieu.get('list_dich_theo_cha', [])),
            'list_cam_theo_cha': len(self.du_lieu.get('list_cam_theo_cha', [])),
            'khung_dich': len(self.du_lieu.get('khung_dich', [])),
            'khung_cam': len(self.du_lieu.get('khung_cam', [])),
        }

    def norm_key(self, key: str) -> str:
        key = (key or '').strip().strip('"\'')
        return re.sub(r'[^a-z0-9]+', '', key.lower())

    def co_key_dich(self, key: str) -> bool:
        return self.norm_key(key) in self.du_lieu['key_dich']

    def co_key_cam(self, key: str) -> bool:
        return self.norm_key(key) in self.du_lieu['key_cam']

    def co_list_dich(self, key: str) -> bool:
        return self.norm_key(key) in self.du_lieu['list_dich_theo_cha']

    def co_list_cam(self, key: str) -> bool:
        return self.norm_key(key) in self.du_lieu['list_cam_theo_cha']

    def co_data_cho_key(self, key: str) -> bool:
        nk = self.norm_key(key)
        return nk in self.du_lieu['key_dich'] or nk in self.du_lieu['key_cam'] or nk in self.du_lieu['list_dich_theo_cha'] or nk in self.du_lieu['list_cam_theo_cha']

    def match_hanh_dong(self, dong: str):
        if not self._da_nap:
            self.nap()
        for entry in self.du_lieu['khung_cam']:
            ket_qua = self._match_entry(entry, dong)
            if ket_qua is not None:
                ket_qua['hanh_dong'] = 'cam'
                return ket_qua
        for entry in self.du_lieu['khung_dich']:
            ket_qua = self._match_entry(entry, dong)
            if ket_qua is not None:
                ket_qua['hanh_dong'] = 'dich'
                return ket_qua
        return None

    def _tao_token(self, loai: str, stt: int) -> str:
        return f'《{loai}{stt}》'

    def _is_hex6(self, value: str) -> bool:
        return len(value) == 6 and all(ch in '0123456789abcdefABCDEF' for ch in value)

    def _is_placeholder_percent(self, token: str) -> bool:
        return bool(re.fullmatch(r'%[A-Za-z0-9_:.\-]{1,80}%', token or ''))

    def _is_placeholder_brace(self, token: str) -> bool:
        if not token or len(token) < 3 or token[0] != '{' or token[-1] != '}':
            return False
        core = token[1:-1].strip()
        if not core or len(core) > 80 or any(ch.isspace() for ch in core):
            return False
        return bool(re.fullmatch(r'[A-Za-z0-9_:.\-]+', core))

    def _is_minimessage_tag(self, token: str) -> bool:
        if not token or len(token) < 3 or token[0] != '<' or token[-1] != '>':
            return False
        core = token[1:-1].strip()
        if not core or len(core) > 120:
            return False
        core_l = core.lower()
        known = {
            'red','blue','green','yellow','white','black','gray','grey','dark_red','dark_blue','dark_green',
            'dark_aqua','aqua','gold','light_purple','dark_purple','bold','italic','underlined','underline',
            'strikethrough','obfuscated','reset','newline','br'
        }
        if core_l in known or core_l.startswith('/'):
            return True
        prefixes = ('#','gradient:','transition:','hover:','click:','insert:','font:','lang:','selector:',
                    'translate:','keybind:','score:','nbt:','fallback:','rainbow','color:','shadow:')
        return core_l.startswith(prefixes)

    def _quet_theo_bo_kiem(self, noi_dung: str, che_p: bool = True, che_h: bool = True, che_c: bool = True, che_f: bool = True):
        text = noi_dung or ''
        out = []
        maps = {'p': {}, 'h': {}, 'c': {}, 'f': {}}
        counts = {'p': 0, 'h': 0, 'c': 0, 'f': 0}
        i = 0
        while i < len(text):
            if che_p and text[i] == '%':
                j = text.find('%', i + 1)
                if j > i + 1:
                    cand = text[i:j+1]
                    if self._is_placeholder_percent(cand):
                        counts['p'] += 1
                        tok = self._tao_token('p', counts['p'])
                        maps['p'][tok] = cand
                        out.append(tok)
                        i = j + 1
                        continue
            if text[i] == '{':
                j = text.find('}', i + 1)
                if j > i + 1:
                    cand = text[i:j+1]
                    if che_p and self._is_placeholder_brace(cand):
                        counts['p'] += 1
                        tok = self._tao_token('p', counts['p'])
                        maps['p'][tok] = cand
                        out.append(tok)
                        i = j + 1
                        continue
                    core = cand[1:-1]
                    if che_h and len(core) == 7 and core[0] == '#' and self._is_hex6(core[1:]):
                        counts['h'] += 1
                        tok = self._tao_token('h', counts['h'])
                        maps['h'][tok] = cand
                        out.append(tok)
                        i = j + 1
                        continue
            if text[i] == '<':
                j = text.find('>', i + 1)
                if j > i + 1 and j - i <= 120:
                    cand = text[i:j+1]
                    core = cand[1:-1]
                    if che_h and len(core) == 7 and core[0] == '#' and self._is_hex6(core[1:]):
                        counts['h'] += 1
                        tok = self._tao_token('h', counts['h'])
                        maps['h'][tok] = cand
                        out.append(tok)
                        i = j + 1
                        continue
                    if che_f and self._is_minimessage_tag(cand):
                        counts['f'] += 1
                        tok = self._tao_token('f', counts['f'])
                        maps['f'][tok] = cand
                        out.append(tok)
                        i = j + 1
                        continue
            if che_h and text.startswith('&#', i):
                cand = text[i:i+8]
                if len(cand) == 8 and self._is_hex6(cand[2:]):
                    counts['h'] += 1
                    tok = self._tao_token('h', counts['h'])
                    maps['h'][tok] = cand
                    out.append(tok)
                    i += 8
                    continue
            if che_h and text[i] == '#':
                cand = text[i:i+7]
                if len(cand) == 7 and self._is_hex6(cand[1:]):
                    prev = text[i-1] if i > 0 else ''
                    if not prev.isalnum():
                        counts['h'] += 1
                        tok = self._tao_token('h', counts['h'])
                        maps['h'][tok] = cand
                        out.append(tok)
                        i += 7
                        continue
            if i + 1 < len(text) and text[i] in '&§':
                code = text[i+1].lower()
                cand = text[i:i+2]
                if che_c and code in '0123456789abcdef':
                    counts['c'] += 1
                    tok = self._tao_token('c', counts['c'])
                    maps['c'][tok] = cand
                    out.append(tok)
                    i += 2
                    continue
                if che_f and code in 'klmnor':
                    counts['f'] += 1
                    tok = self._tao_token('f', counts['f'])
                    maps['f'][tok] = cand
                    out.append(tok)
                    i += 2
                    continue
            out.append(text[i])
            i += 1
        return ''.join(out), maps['p'], maps['h'], maps['c'], maps['f']

    def khoa_placeholder(self, noi_dung: str):
        if not self._da_nap:
            self.nap()
        text, ph_map, _, _, _ = self._quet_theo_bo_kiem(noi_dung, che_p=True, che_h=False, che_c=False, che_f=False)
        return text, ph_map

    def mo_placeholder(self, noi_dung: str, mapping: dict):
        text = self.chuan_hoa_token_meo(noi_dung)
        for token, goc in sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True):
            text = text.replace(token, goc)
        return text

    def khoa_mau(self, noi_dung: str):
        if not self._da_nap:
            self.nap()
        text, _, hex_map, thuong_map, dinh_dang_map = self._quet_theo_bo_kiem(noi_dung, che_p=False, che_h=True, che_c=True, che_f=True)
        return text, hex_map, thuong_map, dinh_dang_map

    def mo_mau(self, noi_dung: str, hex_map: dict, thuong_map: dict, dinh_dang_map: dict):
        text = self.chuan_hoa_token_meo(noi_dung)
        for token, goc in sorted(dinh_dang_map.items(), key=lambda x: len(x[0]), reverse=True):
            text = text.replace(token, goc)
        for token, goc in sorted(thuong_map.items(), key=lambda x: len(x[0]), reverse=True):
            text = text.replace(token, goc)
        for token, goc in sorted(hex_map.items(), key=lambda x: len(x[0]), reverse=True):
            text = text.replace(token, goc)
        return text

    def chuan_hoa_token_meo(self, text: str) -> str:
        text = text or ''
        text = re.sub(r'《\s*([pcfh])(\d+)\s*》', r'《\1\2》', text, flags=re.I)
        return text

    def con_token_noi_bo(self, text: str) -> bool:
        return bool(re.search(r'《[pcfhm]\d+》', text or '', re.I))

    def _nap_common_file(self):
        if not self.file_common.exists():
            return
        payload = self._doc_yaml_or_json(self.file_common)
        # Ho tro ca key cu cua tool va key moi de nhap data nhanh theo file thuc te
        self.du_lieu['key_dich'].update(self.norm_key(x) for x in (payload.get('key_dich_mac_dinh') or payload.get('dich_mac_dinh') or []) if x)
        self.du_lieu['key_cam'].update(self.norm_key(x) for x in (payload.get('key_cam_mac_dinh') or payload.get('cam_mac_dinh') or []) if x)
        self.du_lieu['list_dich_theo_cha'].update(self.norm_key(x) for x in (payload.get('list_dich_theo_cha') or []) if x)
        self.du_lieu['list_cam_theo_cha'].update(self.norm_key(x) for x in (payload.get('list_cam_theo_cha') or []) if x)
        self.du_lieu['placeholder'].extend(payload.get('placeholder_patterns', []))
        self.du_lieu['mau_hex'].extend(payload.get('color_hex_patterns', []) or payload.get('mau_hex_patterns', []))
        self.du_lieu['mau_thuong'].extend(payload.get('color_code_patterns', []) or payload.get('mau_thuong_patterns', []))
        self.du_lieu['dinh_dang'].extend(payload.get('format_code_patterns', []) or payload.get('dinh_dang_patterns', []))

    def _nap_folder_rules(self):
        for path in sorted(self.thu_muc_goc.rglob('khung_dich.yml')):
            self.du_lieu['khung_dich'].extend(self._doc_khung(path, 'dich'))
        for path in sorted(self.thu_muc_goc.rglob('khung_cam.yml')):
            self.du_lieu['khung_cam'].extend(self._doc_khung(path, 'cam'))
        for path in sorted(self.thu_muc_goc.rglob('placeholder.json')):
            payload = self._doc_yaml_or_json(path)
            self.du_lieu['placeholder'].extend(payload.get('patterns', []))
        for path in sorted(self.thu_muc_goc.rglob('mau_sac.json')):
            payload = self._doc_yaml_or_json(path)
            self.du_lieu['mau_hex'].extend(payload.get('hex', []))
            self.du_lieu['mau_thuong'].extend(payload.get('thuong', []))
            self.du_lieu['dinh_dang'].extend(payload.get('dinh_dang', []))

    def _nap_diff_hoc_pattern(self):
        if not self.file_diff.exists():
            return
        try:
            payload = json.loads(self.file_diff.read_text(encoding='utf-8'))
        except Exception:
            return
        pat = payload.get('pattern', {}) if isinstance(payload, dict) else {}
        if isinstance(pat, dict):
            for k, v in pat.get('key_dich', {}).items():
                self.du_lieu['key_dich'].add(self.norm_key(k))
                self.du_lieu['hoc_pattern']['key_dich'][self.norm_key(k)] = v
            for k, v in pat.get('key_cam', {}).items():
                self.du_lieu['key_cam'].add(self.norm_key(k))
                self.du_lieu['hoc_pattern']['key_cam'][self.norm_key(k)] = v
            for k, v in pat.get('list_dich_theo_cha', {}).items():
                self.du_lieu['list_dich_theo_cha'].add(self.norm_key(k))
                self.du_lieu['hoc_pattern']['list_dich_theo_cha'][self.norm_key(k)] = v
            for k, v in pat.get('list_cam_theo_cha', {}).items():
                self.du_lieu['list_cam_theo_cha'].add(self.norm_key(k))
                self.du_lieu['hoc_pattern']['list_cam_theo_cha'][self.norm_key(k)] = v

    def _doc_khung(self, path: Path, loai: str):
        ket_qua = []
        for dong in path.read_text(encoding='utf-8').splitlines():
            dong = dong.rstrip()
            if not dong.strip() or dong.lstrip().startswith('#'):
                continue
            entry = self._tao_entry(dong, loai, str(path))
            if entry:
                ket_qua.append(entry)
        return ket_qua

    def _doc_yaml_or_json(self, path: Path):
        try:
            if path.suffix.lower() == '.json':
                return json.loads(path.read_text(encoding='utf-8'))
            if yaml:
                data = yaml.safe_load(path.read_text(encoding='utf-8'))
                return data or {}
            return {}
        except Exception:
            return {}

    def _tao_entry(self, mau: str, loai: str, nguon: str):
        if '__' not in mau:
            return {'mau': mau, 'loai': loai, 'nguon': nguon, 'co_o_dich': False}
        idx = mau.find('__')
        return {'mau': mau, 'loai': loai, 'nguon': nguon, 'co_o_dich': True, 'prefix': mau[:idx], 'suffix': mau[idx + 2:]}

    def _match_entry(self, entry: dict, dong: str):
        if not entry.get('co_o_dich'):
            if dong == entry['mau'] or dong.strip() == entry['mau'].strip():
                return {'mau': entry['mau'], 'text': '', 'prefix': dong, 'suffix': ''}
            return None
        prefix = entry['prefix']
        suffix = entry['suffix']
        if not dong.startswith(prefix):
            return None
        if suffix:
            if not dong.endswith(suffix):
                return None
            text = dong[len(prefix):len(dong) - len(suffix)]
        else:
            text = dong[len(prefix):]
        return {'mau': entry['mau'], 'text': text, 'prefix': prefix, 'suffix': suffix}

    def _khoa_theo_patterns(self, noi_dung: str, patterns: list[str], loai: str):
        text = noi_dung
        mapping = {}
        stt = 0
        for pat in patterns:
            try:
                regex = re.compile(pat)
            except re.error:
                continue
            def repl(match):
                nonlocal stt
                stt += 1
                token = f'《{loai}{stt}》'
                mapping[token] = match.group(0)
                return token
            text = regex.sub(repl, text)
        return text, mapping

    def _unique(self, ds):
        seen = set()
        out = []
        for item in ds:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out
