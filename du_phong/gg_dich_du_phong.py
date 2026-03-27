from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from urllib.parse import quote

import aiohttp

from tri_nho.bo_nho_dich import bo_nho_dich
from tri_nho.tu_dien_du_phong import tu_dien_du_phong
from tri_nho.manual_hardcore_rules import manual_hardcore_rules
from tri_nho.diff_hoc import diff_hoc
from du_phong.gioi_han_do_dai import gioi_han_do_dai
from du_phong.tach_nho_noi_dung import tach_nho_noi_dung
from du_phong.data_khung_gg import data_khung_gg
from du_phong.bo_dieu_toc_gg import bo_dieu_toc_gg
from du_phong.backend_pool import gg_backend_pool
from loi.backoff import tinh_backoff
from dieu_phoi.ghi_log import tao_trace_logger, trace_logger


@dataclass
class Segment:
    line_idx: int
    path: str
    kind: str
    key: str
    parent: str
    prefix: str
    text: str
    suffix: str
    action: str
    raw_line: str = ''
    raw_value: str = ''


class gg_dich_du_phong:
    def __init__(self, cai_dat=None):
        self.bo_nho = bo_nho_dich()
        self.tu_dien = tu_dien_du_phong()
        self.diff = diff_hoc()
        self.gioi_han = gioi_han_do_dai()
        self.tach_nho = tach_nho_noi_dung()
        self.du_lieu = data_khung_gg()
        self.du_lieu.nap()
        self.timeout = aiohttp.ClientTimeout(total=25, connect=10, sock_read=20)
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
        self.endpoint = 'https://translate.googleapis.com/translate_a/single'
        self.cai_dat = cai_dat
        self.gg_workers = max(1, int(getattr(cai_dat, 'gg_workers', 8) or 8))
        self.gg_min_concurrency = max(1, int(getattr(cai_dat, 'gg_min_concurrency', 2) or 2))
        self.gg_max_concurrency = max(self.gg_min_concurrency, int(getattr(cai_dat, 'gg_max_concurrency', 6) or 6))
        self.gg_chunk_chars = max(120, int(getattr(cai_dat, 'gg_chunk_chars', 1200) or 1200))
        self.gg_rps = float(getattr(cai_dat, 'gg_requests_per_second', 2.2) or 2.2)
        self.gg_retry_count = max(0, int(getattr(cai_dat, 'gg_retry_count', 2) or 2))
        self.gg_fragment_cache_size = max(100, int(getattr(cai_dat, 'gg_fragment_cache_size', 10000) or 10000))
        self.gg_endpoints = list(getattr(cai_dat, 'gg_endpoints', [self.endpoint]) or [self.endpoint])
        self.gg_backend_timeout_ms = max(300, int(getattr(cai_dat, 'gg_backend_timeout_ms', 2500) or 2500))
        self.gg_backend_max_fail = max(1, int(getattr(cai_dat, 'gg_backend_max_fail', 3) or 3))
        self.gg_backend_cooldown_sec = max(1, int(getattr(cai_dat, 'gg_backend_cooldown_sec', 60) or 60))
        self.backend_pool = gg_backend_pool.from_endpoints(
            self.gg_endpoints,
            timeout_ms=self.gg_backend_timeout_ms,
            max_fail=self.gg_backend_max_fail,
            cooldown_sec=self.gg_backend_cooldown_sec,
        )
        self.rate_limiter = bo_dieu_toc_gg(self.gg_rps, self.gg_min_concurrency, self.gg_max_concurrency)
        self.backoff = tinh_backoff(base=float(getattr(cai_dat, 'gg_retry_base_seconds', 1.25) or 1.25), max_time=float(getattr(cai_dat, 'gg_retry_max_seconds', 8.0) or 8.0))
        self._fragment_cache = {}
        self._inflight = {}
        self.manual_rules = manual_hardcore_rules()
        self._runtime_mode = 'auto1'
        self._current_file_name = ''
        self._re_list_item = re.compile(r"^(?P<indent>\s*\-\s*)(?P<value>.*)$")
        self._re_quoted = re.compile(r"^(?P<quote>[\"'])(?P<text>.*?)(?P=quote)$")
        self._re_yaml_key_intrusion = re.compile(r"(^|\s)(?:[A-Za-z_][A-Za-z0-9_\- ]*):")
        self._re_url_domain = re.compile(r'(https?://\S+|www\.[^\s\]"\']+|\b(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b)', re.I)

    async def dich(self, noi_dung: str, lang_from: str = 'auto', lang_to: str = 'vi', trace: trace_logger | None = None, ten_file: str | None = None, mode: str | None = None) -> tuple[str, dict]:
        trace = trace or tao_trace_logger()
        report = {
            'che_do': 'gg_du_phong', 'nguon': 'gg', 'da_tach_nho': False, 'da_dung_bo_nho': False,
            'da_dung_tu_dien': False, 'da_dung_diff_hoc': False, 'so_doan': 1, 'co_loi_gg': False,
            'da_nap_du_lieu': False, 'tong_segment': 0, 'segment_dich': 0, 'segment_cam': 0,
            'segment_cho_data': 0, 'segment_giu_nguyen': 0, 'can_nhap_them_data': False, 'thong_bao': '',
            'trace_id': trace.trace_id, 'trace_file': str(trace.duong_dan), 'segment_logs': []
        }
        self._runtime_mode = (mode or 'auto1').strip() or 'auto1'
        self._current_file_name = (ten_file or '').strip()
        trace.ghi('gg_start', lang_from=lang_from, lang_to=lang_to, mode=self._runtime_mode, ten_file=self._current_file_name, text_goc=noi_dung)
        if not noi_dung or not noi_dung.strip():
            report['nguon'] = 'giu_nguyen_rong'
            return noi_dung, report

        ban_dich_bo_nho = self.bo_nho.lay(noi_dung, lang_from, lang_to)
        if ban_dich_bo_nho and str(ban_dich_bo_nho).strip() != str(noi_dung).strip():
            report['da_dung_bo_nho'] = True
            report['nguon'] = 'bo_nho'
            return ban_dich_bo_nho, report

        ban_dich_tu_dien = self.tu_dien.lay(noi_dung)
        if ban_dich_tu_dien and str(ban_dich_tu_dien).strip() != str(noi_dung).strip():
            report['da_dung_tu_dien'] = True
            report['nguon'] = 'tu_dien'
            self.bo_nho.them(noi_dung, ban_dich_tu_dien, lang_from, lang_to)
            return ban_dich_tu_dien, report

        goi_y = self.diff.lay_goi_y(noi_dung)
        if goi_y and goi_y.get('hanh_dong') == 'da_dich':
            ban_dich_diff = goi_y.get('ban_dich', noi_dung)
            if str(ban_dich_diff).strip() != str(noi_dung).strip():
                report['da_dung_diff_hoc'] = True
                report['nguon'] = 'diff_hoc'
                self.bo_nho.them(noi_dung, ban_dich_diff, lang_from, lang_to)
                return ban_dich_diff, report

        self.du_lieu.nap(force=True)
        report['da_nap_du_lieu'] = True
        lines = noi_dung.splitlines(keepends=True)
        segments = self._phan_tich_segments(lines)
        for seg in segments:
            trace.ghi(
                'segment_parsed',
                vat_the='segment',
                dang_lam='parse_tach_dong',
                line_idx=seg.line_idx,
                kind=seg.kind,
                path=seg.path,
                key=seg.key,
                parent=seg.parent,
                action=seg.action,
                raw=seg.raw_line,
                value_goc=seg.raw_value,
                prefix=seg.prefix,
                text=seg.text,
                suffix=seg.suffix,
            )
        trace.ghi('gg_segment_summary', file_lines=len(lines), tong_segment=len(segments), segment_dich=sum(1 for s in segments if s.action == 'dich_gg'), segment_cam=sum(1 for s in segments if s.action == 'cam'), segment_cho_data=sum(1 for s in segments if s.action == 'cho_data'))
        report['tong_segment'] = len(segments)
        report['segment_dich'] = sum(1 for s in segments if s.action == 'dich_gg')
        report['segment_cam'] = sum(1 for s in segments if s.action == 'cam')
        report['segment_cho_data'] = sum(1 for s in segments if s.action == 'cho_data')
        report['segment_giu_nguyen'] = sum(1 for s in segments if s.action == 'giu_nguyen')
        if report['segment_cho_data'] > 0:
            report['can_nhap_them_data'] = True
            report['thong_bao'] = 'Vui lòng nhập thêm data để tiếp tục sử dụng GG Translate'
        if report['segment_dich'] == 0:
            return noi_dung, report

        async with aiohttp.ClientSession(timeout=self.timeout, headers={'User-Agent': self.user_agent, 'Accept': 'application/json,text/plain,*/*'}) as session:
            translated_parts = await self._chay_hang_doi_segment(segments, lang_from, lang_to, session, report, trace)

        rebuilt = list(lines)
        for idx, replacement in translated_parts:
            if replacement is not None:
                rebuilt[idx] = replacement
        ket_qua = ''.join(rebuilt)
        self.bo_nho.them(noi_dung, ket_qua, lang_from, lang_to)
        trace.ghi('gg_finish', text_tra_ve=ket_qua, co_loi_gg=report.get('co_loi_gg'), segment_logs=report.get('segment_logs', [])[:20])
        return ket_qua, report

    def co_nguy_co_cho_data(self, noi_dung: str) -> bool:
        return any(s.action == 'cho_data' for s in self._phan_tich_segments((noi_dung or '').splitlines(keepends=True)))

    async def _chay_hang_doi_segment(self, segments: list[Segment], lang_from: str, lang_to: str, session: aiohttp.ClientSession, report: dict, trace: trace_logger):
        queue = asyncio.Queue()
        ket_qua = {}
        for seg in segments:
            await queue.put(seg)
        so_worker = min(max(1, self.gg_workers), max(1, len(segments)))
        trace.ghi('segment_queue_start', vat_the='queue', dang_lam='bat_dau_hang_doi_node', tong_segment=len(segments), so_worker=so_worker, min_concurrency=self.gg_min_concurrency, max_concurrency=self.gg_max_concurrency)

        async def _worker(worker_id: int):
            while True:
                try:
                    seg = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                trace.ghi('segment_queue_pick', vat_the='queue', dang_lam='lay_node_khoi_hang_doi', worker_id=worker_id, line_idx=seg.line_idx, path=seg.path, action=seg.action, text=seg.text)
                idx, replacement = await self._dich_segment(seg, lang_from, lang_to, session, report, trace, worker_id=worker_id)
                ket_qua[idx] = replacement
                queue.task_done()

        workers = [asyncio.create_task(_worker(i + 1)) for i in range(so_worker)]
        await queue.join()
        for w in workers:
            if not w.done():
                w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        trace.ghi('segment_queue_finish', vat_the='queue', dang_lam='ket_thuc_hang_doi_node', tong_segment=len(segments), so_worker=so_worker)
        return [(idx, ket_qua.get(idx)) for idx in range(len(segments))]

    async def _dich_segment(self, seg: Segment, lang_from: str, lang_to: str, session: aiohttp.ClientSession, report: dict, trace: trace_logger, worker_id: int | None = None):
        if seg.action != 'dich_gg' or not seg.text.strip():
            ly_do = 'khong_phai_dich_gg' if seg.action != 'dich_gg' else 'text_rong'
            trace.ghi(
                'segment_skipped',
                vat_the='segment',
                dang_lam='bo_qua_khong_gui_gg',
                line_idx=seg.line_idx,
                path=seg.path,
                action=seg.action,
                ly_do=ly_do,
                worker_id=worker_id,
                raw=seg.raw_line,
                value_goc=seg.raw_value,
                prefix=seg.prefix,
                text=seg.text,
                suffix=seg.suffix,
            )
            return seg.line_idx, None

        trace.ghi('segment_start', vat_the='segment', dang_lam='bat_dau_dich', line_idx=seg.line_idx, path=seg.path, action=seg.action, worker_id=worker_id, raw=seg.raw_line, value_goc=seg.raw_value, prefix=seg.prefix, text_goc=seg.text, suffix=seg.suffix)
        try:
            ket_qua = await self._translate_preserve(seg.text, lang_from, lang_to, session, trace, seg)
            translated = ket_qua.get('text')
            report.setdefault('segment_logs', []).append({
                'line_idx': seg.line_idx,
                'path': seg.path,
                'ok': ket_qua.get('ok', True),
                'errors': ket_qua.get('errors', []),
                'sent': ket_qua.get('sent_text', ''),
                'received': ket_qua.get('recv_text', ''),
                'rebuilt': translated or '',
            })
            if translated is None:
                report['co_loi_gg'] = True
                trace.loi('segment_empty', 'translated_none', line_idx=seg.line_idx, path=seg.path, worker_id=worker_id)
                return seg.line_idx, None
            rebuilt_line = f'{seg.prefix}{translated}{seg.suffix}'
            trace.ghi('segment_rebuild', vat_the='segment', dang_lam='rap_lai_dong', line_idx=seg.line_idx, path=seg.path, worker_id=worker_id, prefix=seg.prefix, text_tra_ve=translated, suffix=seg.suffix, text_xuat=rebuilt_line)
            trace.ghi('segment_finish', vat_the='segment', dang_lam='ket_thuc_segment', line_idx=seg.line_idx, path=seg.path, worker_id=worker_id, ok=ket_qua.get('ok', True), errors=ket_qua.get('errors', []), text_tra_ve=translated, text_xuat=rebuilt_line)
            return seg.line_idx, rebuilt_line
        except Exception as e:
            report['co_loi_gg'] = True
            trace.loi('segment_exception', e, line_idx=seg.line_idx, path=seg.path, worker_id=worker_id, text_goc=seg.text)
            return seg.line_idx, None

    def _manual_rule_for_seg(self, seg: Segment | None):
        if seg is None:
            return None
        raw = (seg.text or '').strip()
        if not raw:
            return None
        return self.manual_rules.get(self._current_file_name, raw)

    def _mask_manual_locks(self, text: str, locks: list[str]):
        text = text or ''
        mapping = {}
        for idx, lock in enumerate(sorted([x for x in (locks or []) if x], key=len, reverse=True), 1):
            tok = f'《m{idx}》'
            if lock in text:
                text = text.replace(lock, tok)
                mapping[tok] = lock
        return text, mapping

    def _unmask_manual_locks(self, text: str, mapping: dict[str, str]):
        out = text or ''
        for tok, val in mapping.items():
            out = out.replace(tok, val)
        return out

    async def _translate_preserve(self, text: str, lang_from: str, lang_to: str, session: aiohttp.ClientSession, trace: trace_logger, seg: Segment | None = None):
        original_text = text
        manual_rule = self._manual_rule_for_seg(seg)
        if manual_rule and manual_rule.get('action') == 'skip':
            trace.ghi('manual_rule_skip', vat_the='segment', dang_lam='bo_qua_theo_rule_hardcore', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), truoc=text)
            return {'text': original_text, 'ok': True, 'errors': [], 'sent_text': '', 'recv_text': ''}
        manual_map = {}
        if manual_rule and manual_rule.get('action') == 'lock':
            text, manual_map = self._mask_manual_locks(text, manual_rule.get('locks', []))
            trace.ghi('manual_rule_lock', vat_the='segment', dang_lam='khoa_theo_rule_hardcore', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), truoc=original_text, sau=text, locks=manual_rule.get('locks', []))
        masked, ph_map = self.du_lieu.khoa_placeholder(text)
        trace.ghi('mask_placeholder', vat_the='text', dang_lam='che_placeholder', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), truoc=text, sau=masked, so_token=len(ph_map))
        masked, hex_map, clr_map, fmt_map = self.du_lieu.khoa_mau(masked)
        trace.ghi('mask_color', vat_the='text', dang_lam='che_mau_va_format', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), truoc=text, sau=masked, so_hex=len(hex_map), so_mau=len(clr_map), so_format=len(fmt_map))
        clean_probe = re.sub(r'《[pcfhm]\d+》', '', masked or '').strip()
        if not self._co_text_tu_nhien(clean_probe):
            trace.ghi('segment_skip_no_plain_text', vat_the='text', dang_lam='bo_qua_vi_khong_con_text_tu_nhien', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), truoc=text, sau=masked)
            return {
                'text': original_text,
                'ok': True,
                'errors': [],
                'sent_text': '',
                'recv_text': '',
            }
        translated_masked = await self._translate_masked_text(masked, lang_from, lang_to, session, trace, seg)
        unmasked = self.du_lieu.mo_mau(translated_masked, hex_map, clr_map, fmt_map)
        unmasked = self.du_lieu.mo_placeholder(unmasked, ph_map)
        unmasked = self._unmask_manual_locks(unmasked, manual_map)
        unmasked = self._repair_prefix_and_spacing(original_text, unmasked)
        trace.ghi('unmask_rebuild', vat_the='text', dang_lam='mo_khoa_va_phuc_hoi', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), truoc=translated_masked, sau=unmasked)
        errors = self._ly_do_khong_hop_le_sau_mo(original_text, unmasked)
        trace.ghi('segment_validate', vat_the='text', dang_lam='hau_kiem_segment', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), truoc=original_text, sau=unmasked, ok=(not errors), errors=errors)
        return {
            'text': unmasked,
            'ok': not errors,
            'errors': errors,
            'sent_text': masked,
            'recv_text': translated_masked,
        }

    async def _translate_masked_text(self, masked: str, lang_from: str, lang_to: str, session: aiohttp.ClientSession, trace: trace_logger, seg: Segment | None = None) -> str:
        token_re = re.compile(r'(《[pcfhm]\d+》|https?://\S+|www\.[^\s\]"\']+|\b(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b)', re.I)
        parts = token_re.split(masked or '')
        out = []
        for part in parts:
            if not part:
                continue
            if token_re.fullmatch(part):
                out.append(part)
                continue
            translated = await self._translate_plain_fragment(part, lang_from, lang_to, session, trace, seg)
            out.append(translated)
        return ''.join(out)

    async def _translate_plain_fragment(self, text: str, lang_from: str, lang_to: str, session: aiohttp.ClientSession, trace: trace_logger, seg: Segment | None = None) -> str:
        if not text or not text.strip():
            return text
        if not any(ch.isalpha() for ch in text):
            return text
        use_cache = self._co_the_cache_fragment(text)
        cache_key = (lang_from or 'auto', lang_to or 'vi', text)
        if use_cache and cache_key in self._fragment_cache:
            cached = self._fragment_cache[cache_key]
            trace.ghi('translate_cache_hit', vat_the='fragment', dang_lam='lay_tu_cache_fragment', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), truoc=text, sau=cached)
            return cached
        fut = self._inflight.get(cache_key) if use_cache else None
        if fut is not None:
            trace.ghi('translate_dedupe_wait', vat_the='fragment', dang_lam='cho_ket_qua_cung_noi_dung', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), truoc=text)
            return await fut
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        if use_cache:
            self._inflight[cache_key] = fut
        try:
            trace.ghi('translate_send', vat_the='fragment', dang_lam='gui_google_translate', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), truoc=text)
            translated = await self._goi_google_dich(text, lang_from, lang_to, session, trace, seg)
            trace.ghi('translate_recv', vat_the='fragment', dang_lam='nhan_google_translate', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), truoc=text, sau=translated)
            translated = (translated or text).replace('```', '')
            if self._re_yaml_key_intrusion.search(translated) and not self._re_yaml_key_intrusion.search(text):
                translated = text
            if len(self._fragment_cache) >= self.gg_fragment_cache_size:
                self._fragment_cache.pop(next(iter(self._fragment_cache)))
            self._fragment_cache[cache_key] = translated
            if not fut.done():
                fut.set_result(translated)
            return translated
        except Exception as e:
            if not fut.done():
                fut.set_result(text)
            trace.loi('translate_fragment_exception', e, line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), text_gui_di=text)
            return text
        finally:
            self._inflight.pop(cache_key, None)

    def _repair_or_fallback(self, original_masked: str, translated_masked: str) -> str:
        text = self.du_lieu.chuan_hoa_token_meo(translated_masked or '')
        original_tokens = re.findall(r'《[pcfhm]\d+》', original_masked)
        translated_tokens = re.findall(r'《[pcfhm]\d+》', text)
        if len(original_tokens) != len(translated_tokens):
            return original_masked
        if self._re_yaml_key_intrusion.search(text) and not self._re_yaml_key_intrusion.search(original_masked):
            return original_masked
        if set(translated_tokens) != set(original_tokens):
            return original_masked
        return text

    def _repair_prefix_and_spacing(self, goc: str, da_mo: str) -> str:
        goc = goc or ''
        da_mo = da_mo or ''
        if not goc.strip() or not da_mo.strip():
            return da_mo or goc

        def _tach_rawmsg_prefix(text: str):
            m = re.match(r'(?is)^(\s*\[console\]\s*rawmsg\s+)(%[^%\s]+%)(\s+)(true|false)(\s+)(.*)$', text or '')
            if not m:
                return None
            return m.group(1) + m.group(2) + m.group(3) + m.group(4) + m.group(5), m.group(6)

        def _tach_tmmsg_prefix(text: str):
            m = re.match(r'(?is)^(\s*\[console\]\s*tm\s+msg\s+)(%[^%\s]+%)(\s+)(.*)$', text or '')
            if not m:
                return None
            return m.group(1) + m.group(2) + m.group(3), m.group(4)

        def _tach_tag_prefix(text: str):
            m = re.match(r'(?is)^(\s*)(\[(?:message|broadcast|minimessage|minibroadcast)\])(\s*)(.*)$', text or '')
            if not m:
                return None
            return m.group(1) + m.group(2) + ' ', m.group(4)

        def _strip_tag_noise(text: str):
            return re.sub(r'^\s*\[[^\]\n]+\]\s*', '', text or '', count=1)

        def _strip_rawmsg_noise(text: str):
            text = text or ''
            text = re.sub(r'(?is)^\s*\[console\]\s*rawmsg\s*', '', text, count=1)
            text = re.sub(r'(?is)^%[^%\s]+%\s*', '', text, count=1)
            text = re.sub(r'(?is)^(?:true|false|đúng vậy|đúng|sai)\s*', '', text, count=1)
            return text

        def _strip_tmmsg_noise(text: str):
            text = text or ''
            text = re.sub(r'(?is)^\s*\[console\]\s*tm\s+msg\s*', '', text, count=1)
            text = re.sub(r'(?is)^%[^%\s]+%\s*', '', text, count=1)
            return text

        repairers = (
            (_tach_rawmsg_prefix, _strip_rawmsg_noise),
            (_tach_tmmsg_prefix, _strip_tmmsg_noise),
            (_tach_tag_prefix, _strip_tag_noise),
        )
        for fn, cleaner in repairers:
            g = fn(goc)
            if not g:
                continue
            prefix_goc, _ = g
            d = fn(da_mo)
            rest_moi = d[1] if d else cleaner(da_mo)
            rest_moi = (rest_moi or '').lstrip()
            return prefix_goc + rest_moi
        return da_mo

    def _ly_do_khong_hop_le_sau_mo(self, goc: str, da_mo: str) -> list[str]:
        loi = []
        if self.du_lieu.con_token_noi_bo(da_mo):
            loi.append('con_token_noi_bo')
        pats = [r'%[^%\s]+%', r'\{[^{}\n]+\}', r'<[^<>\n]+>', r'&[0-9a-fA-F]', r'§[0-9a-fA-F]', r'&[k-orK-OR]', r'§[k-orK-OR]', r'&#[0-9A-Fa-f]{6}']
        for pat in pats:
            if len(re.findall(pat, goc or '')) != len(re.findall(pat, da_mo or '')):
                loi.append(f'lech_token:{pat}')
        if self._re_url_domain.search(goc or ''):
            urls_goc = sorted(set(self._re_url_domain.findall(goc or '')))
            urls_moi = sorted(set(self._re_url_domain.findall(da_mo or '')))
            if urls_goc != urls_moi:
                loi.append('url_domain_bi_doi')
        return loi

    def _tach_chunk_theo_node(self, text: str) -> list[str]:
        text = text or ''
        if not self.gioi_han.can_tach(text, self.gg_chunk_chars):
            return [text]
        chunks = []
        hien_tai = ''
        for part in re.split(r'([.!?\n]+)', text):
            if not part:
                continue
            if len(hien_tai) + len(part) <= self.gg_chunk_chars:
                hien_tai += part
                continue
            if hien_tai:
                chunks.append(hien_tai)
            if len(part) <= self.gg_chunk_chars:
                hien_tai = part
            else:
                chunks.extend(self.tach_nho.tach(part, gioi_han=self.gg_chunk_chars))
                hien_tai = ''
        if hien_tai:
            chunks.append(hien_tai)
        return [c for c in chunks if c]

    async def _goi_google_dich(self, text: str, lang_from: str, lang_to: str, session: aiohttp.ClientSession, trace: trace_logger | None = None, seg: Segment | None = None):
        if self.gioi_han.can_tach(text, self.gg_chunk_chars):
            chunks = self._tach_chunk_theo_node(text)
            if trace:
                trace.ghi('gg_chunk_split', vat_the='text', dang_lam='tach_theo_node_lon', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), truoc=text, sau=chunks, so_chunk=len(chunks))
            out = []
            for chunk in chunks:
                out.append(await self._goi_google_dich(chunk, lang_from, lang_to, session, trace, seg))
            return ''.join(out)
        sl = 'auto' if lang_from == 'auto' else lang_from
        tl = lang_to or 'vi'
        q = quote(text)
        backends = self.backend_pool.ordered()
        if not backends:
            backends = self.backend_pool.backends
        for backend_idx, backend in enumerate(backends, start=1):
            if not backend.is_available():
                if trace:
                    trace.ghi('backend_skip', vat_the='backend', dang_lam='bo_qua_backend_dang_cooldown', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), backend=backend.name, ly_do='cooldown', text_gui_di=text)
                continue
            url = f'{backend.base_url}?client=gtx&sl={sl}&tl={tl}&dt=t&q={q}'
            lan = 0
            while True:
                await self.rate_limiter.cho_luot()
                await self.rate_limiter.vao_backend()
                try:
                    if trace:
                        trace.ghi('backend_send', vat_the='backend', dang_lam='gui_google_translate_backend', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), backend=backend.name, backend_idx=backend_idx, text_gui_di=text, lan_thu=lan + 1, current_concurrency=self.rate_limiter.current_concurrency)
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=max(1.0, backend.timeout_ms / 1000.0))) as resp:
                        if resp.status == 429:
                            backend.mark_fail()
                            await self.rate_limiter.bao_that_bai_tam_thoi()
                            if trace:
                                trace.loi('backend_http_429', f'status={resp.status}', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), backend=backend.name, text_gui_di=text, lan_thu=lan + 1)
                            if lan < self.gg_retry_count:
                                await asyncio.sleep(self.backoff.tinh(lan + 1))
                                lan += 1
                                continue
                            if trace:
                                trace.ghi('backend_fallback', vat_the='backend', dang_lam='chuyen_backend_vi_429', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), backend=backend.name, text_gui_di=text)
                            break
                        if resp.status >= 500:
                            backend.mark_fail()
                            await self.rate_limiter.bao_that_bai_tam_thoi()
                            if trace:
                                trace.loi('backend_http_5xx', f'status={resp.status}', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), backend=backend.name, text_gui_di=text, lan_thu=lan + 1)
                            if lan < self.gg_retry_count:
                                await asyncio.sleep(self.backoff.tinh(lan + 1))
                                lan += 1
                                continue
                            if trace:
                                trace.ghi('backend_fallback', vat_the='backend', dang_lam='chuyen_backend_vi_5xx', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), backend=backend.name, text_gui_di=text)
                            break
                        if resp.status != 200:
                            backend.mark_fail()
                            if trace:
                                trace.loi('backend_http_error', f'status={resp.status}', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), backend=backend.name, text_gui_di=text, lan_thu=lan + 1)
                            break
                        data = await resp.json(content_type=None)
                        if not isinstance(data, list) or not data or not isinstance(data[0], list):
                            backend.mark_fail()
                            await self.rate_limiter.bao_that_bai_tam_thoi()
                            if trace:
                                trace.loi('backend_data_invalid', 'du_lieu_khong_hop_le', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), backend=backend.name, text_gui_di=text, output=data)
                            if lan < self.gg_retry_count:
                                await asyncio.sleep(self.backoff.tinh(lan + 1))
                                lan += 1
                                continue
                            break
                        translated = ''.join(part[0] for part in data[0] if isinstance(part, list) and part and isinstance(part[0], str)) or text
                        backend.mark_success()
                        await self.rate_limiter.bao_thanh_cong()
                        if trace:
                            trace.ghi('backend_recv', vat_the='backend', dang_lam='nhan_google_translate_backend', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), backend=backend.name, text_gui_di=text, text_tra_ve=translated, lan_thu=lan + 1)
                        return translated
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    backend.mark_fail()
                    await self.rate_limiter.bao_that_bai_tam_thoi()
                    if trace:
                        trace.loi('backend_network_error', e, line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), backend=backend.name, text_gui_di=text, lan_thu=lan + 1)
                    if lan < self.gg_retry_count:
                        await asyncio.sleep(self.backoff.tinh(lan + 1))
                        lan += 1
                        continue
                    if trace:
                        trace.ghi('backend_fallback', vat_the='backend', dang_lam='chuyen_backend_vi_mang', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), backend=backend.name, text_gui_di=text)
                    break
                except Exception as e:
                    backend.mark_fail()
                    await self.rate_limiter.bao_that_bai_tam_thoi()
                    if trace:
                        trace.loi('backend_exception', e, line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), backend=backend.name, text_gui_di=text, lan_thu=lan + 1)
                    break
                finally:
                    await self.rate_limiter.ra_backend()
        if trace:
            trace.loi('backend_all_failed', 'khong_backend_nao_thanh_cong', line_idx=getattr(seg, 'line_idx', None), path=getattr(seg, 'path', ''), text_gui_di=text)
        return text

    def _tach_duoi_comment(self, text: str) -> tuple[str, str]:
        in_single = False
        in_double = False
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == "'" and not in_double:
                if in_single and i + 1 < len(text) and text[i + 1] == "'":
                    i += 2
                    continue
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == '#' and not in_single and not in_double:
                return text[:i], text[i:]
            i += 1
        return text, ''

    def _tim_colon_ngoai_quote(self, text: str) -> int:
        in_single = False
        in_double = False
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == "'" and not in_double:
                if in_single and i + 1 < len(text) and text[i + 1] == "'":
                    i += 2
                    continue
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif ch == ':' and not in_single and not in_double:
                return i
            i += 1
        return -1

    def _tach_key_value_stateful(self, line: str):
        khong_comment, tail = self._tach_duoi_comment(line)
        idx = self._tim_colon_ngoai_quote(khong_comment)
        if idx < 0:
            return None
        before = khong_comment[:idx]
        after = khong_comment[idx + 1:]
        if not before.strip():
            return None
        indent_len = len(before) - len(before.lstrip(' 	'))
        indent = before[:indent_len]
        key_raw = before[indent_len:]
        if not key_raw.strip():
            return None
        sep = ':'
        if after.startswith(' '):
            sep += after[:len(after) - len(after.lstrip(' '))]
            after = after[len(sep)-1:]
        return {
            'indent': indent,
            'key': key_raw,
            'sep': sep,
            'value': after,
            'tail': tail,
        }


    def _tach_prefix_command(self, text: str) -> tuple[str, str]:
        text = text or ''
        if not text:
            return '', text
        leading = text[:len(text) - len(text.lstrip(' '))]
        body = text.lstrip(' ')
        lowered = body.lower()

        for tag in ('[message]', '[broadcast]', '[minimessage]', '[minibroadcast]'):
            if lowered.startswith(tag):
                rest = body[len(tag):]
                spaces = rest[:len(rest) - len(rest.lstrip(' '))]
                return leading + body[:len(tag)] + spaces, rest.lstrip(' ')

        m = re.match(r'(?is)^(\[console\]\s*rawmsg\s+)(%[^%\s]+%)(\s+)(true|false)(\s+)(.*)$', body)
        if m:
            fixed = leading + m.group(1) + m.group(2) + m.group(3) + m.group(4) + m.group(5)
            return fixed, m.group(6)

        m = re.match(r'(?is)^(\[console\]\s*tm\s+msg\s+)(%[^%\s]+%)(\s+)(.*)$', body)
        if m:
            fixed = leading + m.group(1) + m.group(2) + m.group(3)
            return fixed, m.group(4)

        return '', text

    def _co_text_tu_nhien(self, text: str) -> bool:
        text = text or ''
        if not bool(re.search(r'[A-Za-zÀ-ỹ]', text)):
            return False
        if self._runtime_mode == 'auto3':
            words = re.findall(r'[A-Za-zÀ-ỹ]+', text)
            if len(words) == 1 and len(words[0]) <= 2:
                return False
        return True

    def _co_the_cache_fragment(self, text: str) -> bool:
        text = text or ''
        if not text.strip():
            return False
        if self._re_url_domain.search(text):
            return False
        if self._runtime_mode in {'auto2', 'auto3', 'hardcore'}:
            return False
        if '[' in text or ']' in text or '%' in text:
            return False
        if re.search(r'\b(?:rawmsg|tm\s+msg|openguimenu|warp|points\s+take|lp\s+user)\b', text, re.I):
            return False
        if text.strip().startswith('<') and text.strip().endswith('>'):
            return False
        return True

    def _tach_gia_tri_de_dich(self, value: str, tail: str):
        value = value or ''
        leading = value[:len(value) - len(value.lstrip())]
        trailing = value[len(value.rstrip()):]
        core = value.strip()

        def split_with_quote(inner: str, q: str | None):
            extra_prefix, inner_text = self._tach_prefix_command(inner)
            if q:
                return leading + q + extra_prefix, inner_text, q + trailing + tail
            return leading + extra_prefix, inner_text, trailing + tail

        if len(core) >= 2 and core[0] in {"'", '"'} and core[-1] == core[0]:
            q = core[0]
            inner = core[1:-1]
            return split_with_quote(inner, q)

        extra_prefix, inner_text = self._tach_prefix_command(core)
        if extra_prefix:
            return leading + extra_prefix, inner_text, trailing + tail

        return leading, core or value, trailing + tail

    def _node_kind(self, key: str, parent: str, kind: str) -> str:
        nk = self.du_lieu.norm_key(key)
        np = self.du_lieu.norm_key(parent)
        if kind == 'list_item' and np == 'lore':
            return 'lore_item'
        if nk in {'displayname', 'display_name', 'name', 'menu_title', 'title', 'subtitle'}:
            return 'display_text'
        if nk == 'lore' or np == 'lore':
            return 'lore_item'
        if np in {'clickcommands', 'leftclickcommands', 'rightclickcommands', 'denycommands'}:
            return 'command_item'
        if nk in {'permission', 'material', 'slot', 'size', 'type', 'open_command', 'register_command'}:
            return 'technical'
        return 'generic'

    def _context_allows_translate(self, key: str, parent: str, kind: str, value: str) -> bool:
        node_kind = self._node_kind(key, parent, kind)
        if node_kind in {'display_text', 'lore_item'}:
            return True
        if node_kind == 'command_item':
            return self._co_the_dich_lenh_message(value) or (value or '').strip().lower().startswith('[console] rawmsg')
        return False

    def _build_list_path(self, path_stack: list[tuple[int, str]], parent: str, list_counts: dict[str, int]) -> str:
        base = '.'.join([p for _, p in path_stack])
        if parent:
            base = base or parent
        if not base:
            return ''
        idx = list_counts.get(base, 0)
        list_counts[base] = idx + 1
        return f'{base}[{idx}]'

    def _phan_tich_segments(self, lines: list[str]):
        segments = []
        parent_stack: list[tuple[int, str]] = []
        path_stack: list[tuple[int, str]] = []
        list_counts: dict[str, int] = {}
        for idx, raw in enumerate(lines):
            line = raw.rstrip('\r\n')
            if not line.strip() or line.lstrip().startswith('#'):
                segments.append(Segment(idx, '', 'comment', '', '', '', '', raw[len(line):], 'giu_nguyen', raw_line=raw, raw_value=''))
                continue

            m_key_value = self._tach_key_value_stateful(line)
            if m_key_value is not None:
                indent = len(m_key_value['indent'].replace('	', '  '))
                key = m_key_value['key'].strip().strip("\"'")
                value = m_key_value['value']
                tail = (m_key_value['tail'] or '') + raw[len(line):]
                while parent_stack and parent_stack[-1][0] >= indent:
                    parent_stack.pop()
                while path_stack and path_stack[-1][0] >= indent:
                    path_stack.pop()
                parent = parent_stack[-1][1] if parent_stack else ''
                path = '.'.join([p for _, p in path_stack] + [key])
                if not (value or '').strip():
                    parent_stack.append((indent, key))
                    path_stack.append((indent, key))
                    segments.append(Segment(idx, path, 'key_only', key, parent, line, raw[len(line):], '', 'giu_nguyen', raw_line=raw, raw_value=''))
                    continue
                action = self._xac_dinh_action_value(key, parent, value, kind='key_value')
                extra_prefix, text_gia_tri, suffix = self._tach_gia_tri_de_dich(value, tail)
                prefix = f"{m_key_value['indent']}{m_key_value['key']}{m_key_value['sep']}" + extra_prefix
                segments.append(Segment(idx, path, 'key_value', key, parent, prefix, text_gia_tri, suffix, action, raw_line=raw, raw_value=value))
                continue

            khong_comment, tail = self._tach_duoi_comment(line)
            if khong_comment.rstrip().endswith(':') and self._tim_colon_ngoai_quote(khong_comment.rstrip()[:-1]) < 0:
                indent_len = len(khong_comment) - len(khong_comment.lstrip(' 	'))
                indent = len(khong_comment[:indent_len].replace('	', '  '))
                key = khong_comment[indent_len:].rstrip()[:-1].strip().strip('"\'')
                while parent_stack and parent_stack[-1][0] >= indent:
                    parent_stack.pop()
                while path_stack and path_stack[-1][0] >= indent:
                    path_stack.pop()
                parent = parent_stack[-1][1] if parent_stack else ''
                path = '.'.join([p for _, p in path_stack] + [key])
                parent_stack.append((indent, key))
                path_stack.append((indent, key))
                segments.append(Segment(idx, path, 'key_only', key, parent, line, raw[len(line):], '', 'giu_nguyen', raw_line=raw, raw_value=''))
                continue

            m_list = self._re_list_item.match(line)
            if m_list:
                indent = len(m_list.group('indent').replace('	', '  '))
                while parent_stack and parent_stack[-1][0] >= indent:
                    parent_stack.pop()
                while path_stack and path_stack[-1][0] >= indent:
                    path_stack.pop()
                parent = parent_stack[-1][1] if parent_stack else ''
                path = self._build_list_path(path_stack, parent, list_counts)
                khong_comment, tail = self._tach_duoi_comment(m_list.group('value'))
                value = khong_comment
                action = self._xac_dinh_action_list(parent, value, kind='list_item')
                extra_prefix, text_gia_tri, suffix = self._tach_gia_tri_de_dich(value, tail + raw[len(line):])
                segments.append(Segment(idx, path, 'list_item', '', parent, m_list.group('indent') + extra_prefix, text_gia_tri, suffix, action, raw_line=raw, raw_value=value))
                continue

            segments.append(Segment(idx, '', 'raw', '', '', line, raw[len(line):], '', 'giu_nguyen', raw_line=raw, raw_value=''))
        return segments

    def _tach_text_suffix(self, value: str, tail: str):
        return self._tach_gia_tri_de_dich(value, tail)

    def _co_the_dich_lenh_message(self, value: str) -> bool:
        text = (value or '').strip()
        if len(text) >= 2 and text[0] in {"'", '"'} and text[-1] == text[0]:
            text = text[1:-1].strip()
        return any(text.lower().startswith(tag) for tag in ('[message]', '[broadcast]', '[minimessage]', '[minibroadcast]'))

    def _looks_translatable_text(self, value: str) -> bool:
        value = (value or '').strip()
        if not value:
            return False
        if value.lower() in {'true', 'false', 'null'}:
            return False
        if re.fullmatch(r'-?\d+(?:\.\d+)?', value):
            return False
        if re.fullmatch(r'[A-Z0-9_\-:.]+', value):
            return False
        if '/' in value and ' ' not in value:
            return False
        return any(ch.isalpha() for ch in value)

    def _xac_dinh_action_value(self, key: str, parent: str, value: str, kind: str = 'key_value') -> str:
        nk = self.du_lieu.norm_key(key)
        if nk in {'clickcommands', 'leftclickcommands', 'rightclickcommands', 'denycommands'}:
            lower = (value or '').strip().lower().strip("'").strip('\"')
            if lower.startswith('[console] rawmsg'):
                return 'dich_gg'
            return 'dich_gg' if self._co_the_dich_lenh_message(value) else 'cam'
        if self.du_lieu.co_key_cam(key):
            return 'cam'
        if self.du_lieu.co_key_dich(key):
            return 'dich_gg' if self._context_allows_translate(key, parent, kind, value) else 'cam'
        return 'cho_data' if self.du_lieu.co_data_cho_key(parent) or self.du_lieu.co_data_cho_key(key) or self._looks_translatable_text(value) else 'giu_nguyen'

    def _xac_dinh_action_list(self, parent: str, value: str, kind: str = 'list_item') -> str:
        np = self.du_lieu.norm_key(parent)
        if np in {'clickcommands', 'leftclickcommands', 'rightclickcommands', 'denycommands'}:
            lower = (value or '').strip().lower().strip("'").strip('\"')
            if lower.startswith('[console] rawmsg'):
                return 'dich_gg'
            return 'dich_gg' if self._co_the_dich_lenh_message(value) else 'cam'
        if self.du_lieu.co_list_cam(parent):
            return 'cam'
        if self.du_lieu.co_list_dich(parent):
            return 'dich_gg' if self._context_allows_translate('', parent, kind, value) else 'cam'
        return 'cho_data' if self.du_lieu.co_data_cho_key(parent) or self._looks_translatable_text(value) else 'giu_nguyen'
