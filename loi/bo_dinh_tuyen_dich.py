from __future__ import annotations

import re

from cau_hinh.cai_dat import cai_dat_mac_dinh, cai_dat_he_thong
from loi.gemini_loi import gemini_loi
from loi.quan_ly_key import quan_ly_key
from du_phong.gg_dich_du_phong import gg_dich_du_phong
from tri_nho.diff_hoc import diff_hoc
from hau_kiem.kiem_tra_ban_dich import kiem_tra_ban_dich
from dieu_phoi.ghi_log import tao_trace_logger


class bo_dinh_tuyen_dich:
    def __init__(self, cai_dat=cai_dat_mac_dinh):
        self.cai_dat = cai_dat
        self.gemini = gemini_loi(cai_dat)
        self.quan_ly_key = quan_ly_key(cai_dat.gemini_api_keys)
        self.gg = gg_dich_du_phong(cai_dat)
        self.diff = diff_hoc()
        self.hau_kiem = kiem_tra_ban_dich()
        self._dau_van_tay_key = self._tao_dau_van_tay_key(cai_dat.gemini_api_keys)

    def _tao_dau_van_tay_key(self, ds_key) -> tuple[str, ...]:
        return tuple(sorted(k.strip() for k in (ds_key or []) if k and k.strip() and not k.startswith('YOUR_')))

    def _lam_moi_gemini_neu_can(self):
        cai_dat_moi = cai_dat_he_thong()
        dau_van_tay_moi = self._tao_dau_van_tay_key(cai_dat_moi.gemini_api_keys)
        if dau_van_tay_moi != self._dau_van_tay_key:
            self.cai_dat = cai_dat_moi
            self.gemini = gemini_loi(cai_dat_moi)
            self.quan_ly_key = quan_ly_key(cai_dat_moi.gemini_api_keys)
            self._dau_van_tay_key = dau_van_tay_moi
            return
        if not getattr(self.gemini, 'keys', None) and dau_van_tay_moi:
            self.cai_dat = cai_dat_moi
            self.gemini = gemini_loi(cai_dat_moi)
            self.quan_ly_key = quan_ly_key(cai_dat_moi.gemini_api_keys)
            self._dau_van_tay_key = dau_van_tay_moi

    def _don_output_sau_gemini(self, noi_dung_goc: str, ban_dich: str) -> str:
        text = ban_dich or ''
        text = text.replace('```yaml', '').replace('```yml', '').replace('```json', '').replace('```', '')
        lines = []
        for dong in text.splitlines():
            dong_sach = dong.strip()
            if not dong_sach:
                lines.append('')
                continue
            lower = dong_sach.lower()
            if lower.startswith('# translated by ') or lower.startswith('# model:') or lower.startswith('# language:'):
                continue
            lines.append(dong.rstrip())
        text = '\n'.join(lines)
        text = re.sub(r'([&§][0-9a-fk-orA-FK-OR])\s+', r'\1', text)
        if '\n' in noi_dung_goc:
            text = '\n'.join(d.rstrip() for d in text.splitlines())
        return text.strip()

    def _dat_chuan(self, goc: str, dich: str) -> tuple[bool, dict]:
        bao_cao = self.hau_kiem.kiem_tra(goc, dich)
        return bool(bao_cao.get('hop_le')), bao_cao

    async def dich(self, noi_dung: str, ten_file: str, lang_from: str = 'auto', lang_to: str = 'vi', file_type: str = 'text', mode: str = 'auto1') -> tuple[str, dict]:
        trace = tao_trace_logger()
        trace.ghi('router_start', file=ten_file, lang_from=lang_from, lang_to=lang_to, file_type=file_type, mode=mode, text_goc=noi_dung)
        self._lam_moi_gemini_neu_can()
        co_key = bool(getattr(self.gemini, 'keys', None)) and bool(getattr(self.cai_dat, 'use_gemini', True))
        if co_key:
            trace.ghi('gemini_send', file=ten_file, text_gui_di=noi_dung)
            ban_dich, thanh_cong = await self.gemini.translate_text(noi_dung, ten_file, lang_from, lang_to, file_type)
            trace.ghi('gemini_recv', file=ten_file, ok=thanh_cong, text_tra_ve=ban_dich)
            if thanh_cong:
                ban_dich = self._don_output_sau_gemini(noi_dung, ban_dich)
                hop_le, bao_cao = self._dat_chuan(noi_dung, ban_dich)
                trace.ghi('gemini_validate', file=ten_file, ok=hop_le, output=bao_cao)
                if hop_le:
                    if bool(getattr(self.cai_dat, 'learn_from_gemini', True)):
                        self.diff.hoc_tu_cap(noi_dung, ban_dich)
                    return ban_dich, {
                        'nguon': 'gemini',
                        'so_key': len(self.gemini.keys),
                        'model': self.gemini.get_current_model(),
                        'final': True,
                        'skip_gg': True,
                        'hau_kiem': bao_cao,
                        'trace_id': trace.trace_id,
                        'trace_file': str(trace.duong_dan),
                        'ban_dich_tho': ban_dich,
                    }
        if not bool(getattr(self.cai_dat, 'use_gg', True)):
            trace.ghi('router_finish', file=ten_file, nguon='giu_nguyen_do_tat_gg', text_xuat=noi_dung)
            return noi_dung, {'nguon': 'giu_nguyen_do_tat_gg', 'co_key_gemini': co_key, 'hau_kiem': {'hop_le': True, 'loi': []}, 'trace_id': trace.trace_id, 'trace_file': str(trace.duong_dan), 'ban_dich_tho': noi_dung}
        ban_dich_gg, report = await self.gg.dich(noi_dung, lang_from, lang_to, trace=trace, ten_file=ten_file, mode=mode)
        hop_le_gg, bao_cao_gg = self._dat_chuan(noi_dung, ban_dich_gg)
        trace.ghi('gg_validate', file=ten_file, ok=hop_le_gg, output=bao_cao_gg, text_tra_ve=ban_dich_gg)
        if isinstance(report, dict):
            report.setdefault('co_key_gemini', co_key)
            report['mode'] = mode
            report['hau_kiem'] = bao_cao_gg
            report['fallback_tu_gemini'] = co_key
            report['trace_id'] = trace.trace_id
            report['trace_file'] = str(trace.duong_dan)
            report['ban_dich_tho'] = ban_dich_gg
            report['ban_xuat_de_xuat'] = noi_dung if not hop_le_gg else ban_dich_gg
            report['can_xuat_goc'] = not hop_le_gg
            if not hop_le_gg:
                report['nguon'] = 'gg_fail_check_chua_rollback'
        trace.ghi('router_finish', file=ten_file, nguon=(report or {}).get('nguon'), text_tra_ve=ban_dich_gg, text_xuat=(noi_dung if not hop_le_gg else ban_dich_gg))
        return ban_dich_gg, report
