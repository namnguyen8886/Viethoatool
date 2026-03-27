"""API REST cho tool dịch, tách panel HTML/CSS/JS để dễ chỉnh và mở rộng cho bot/API."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
import zipfile
import hashlib
from pathlib import Path
from typing import Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from giao_tiep.schemas import (
    ApiResponse,
    ErrorDetail,
    MetaResponse,
    GeminiPromptUpdateRequest,
    PluginModifyRequest,
    RunBody,
    SettingsData,
    SettingsUpdateRequest,
    ShieldCheckRequest,
    TranslateFileRequest,
    TranslateTextRequest,
)

from dieu_phoi.quan_ly_job import quan_ly_job, job
from dieu_phoi.ghi_log import log, tao_trace_logger
from xu_ly_file.quet_sau import quet_sau
from xu_ly_file.quet_folder_ngoai import quet_folder_ngoai
from xu_ly_file.trich_noi_dung import trich_noi_dung
from xu_ly_file.phan_loai_file import phan_loai_file
from xu_ly_file.lap_lai_file import lap_lai_file
from xu_ly_file.tai_len_gofile import tai_len_gofile
from xu_ly_file.dong_goi import dong_goi
from loi.bo_dinh_tuyen_dich import bo_dinh_tuyen_dich
from loi.gemini_loi import bo_nhan_dien_ngon_ngu
from hau_kiem.kiem_tra_ban_dich import kiem_tra_ban_dich
from hau_kiem.bao_cao import bao_cao as bao_cao_cls
from tri_nho.du_lieu_plugin_can_dao import du_lieu_plugin_can_dao
from cau_hinh.hang_so import thu_muc_tam, thu_muc_ket_qua
from cau_hinh.cai_dat import cai_dat_mac_dinh
from dieu_phoi.fallback_modes import AUTO_MODES

app = FastAPI(title='He Thong Dich Day Du', version='3.1.2', docs_url='/api/docs')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

_ql = quan_ly_job()
_quet = quet_sau()
_quet_ng = quet_folder_ngoai()
_trich = trich_noi_dung()
_phanloai = phan_loai_file()
_lap = lap_lai_file()
_zipper = dong_goi()
_router = bo_dinh_tuyen_dich(cai_dat_mac_dinh)
_uploader = tai_len_gofile()
_valid = kiem_tra_ban_dich()
_reporter = bao_cao_cls()
_plugins = du_lieu_plugin_can_dao()
START_TS = int(time.time())

THU_MUC_WEB = Path(__file__).resolve().parent / 'web'
THU_MUC_WEB.mkdir(parents=True, exist_ok=True)
INDEX_HTML = THU_MUC_WEB / 'index.html'
PROMPT_FILE = Path(__file__).resolve().parents[1] / 'du_lieu' / 'gemini_prompt_style.txt'
PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
if not PROMPT_FILE.exists():
    PROMPT_FILE.write_text('Hãy dịch tự nhiên, giữ nguyên placeholder, mã màu, command và cấu trúc file.', encoding='utf-8')

app.mount('/static', StaticFiles(directory=str(THU_MUC_WEB)), name='static')


def _meta() -> MetaResponse:
    return MetaResponse(request_id=f'req_{uuid.uuid4().hex[:10]}', timestamp=int(time.time()))


def _ok(data: Any = None, message: str = 'OK') -> ApiResponse:
    return ApiResponse(ok=True, message=message, data=data, error=None, meta=_meta())


def _err(code: str, message: str, detail: str | None = None, status_code: int = 400):
    raise HTTPException(
        status_code=status_code,
        detail=ApiResponse(
            ok=False,
            message=message,
            data=None,
            error=ErrorDetail(code=code, detail=detail),
            meta=_meta(),
        ).model_dump()
    )


def _safe_name(name: str) -> str:
    ten = Path(name or 'upload.zip').name
    ten = ten.replace('..', '_').replace(chr(92), '_').replace('/', '_').strip()
    return ten or 'upload.zip'


def _doc_json(path: Path, default: Any):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, type(default)) else default
    except Exception:
        return default


def _serialize_job(j: job) -> dict[str, Any]:
    scan = j.ket_qua.get('scan', {}) if isinstance(j.ket_qua, dict) else {}
    total = len(scan.get('can_dich', []) or [])
    done_count = sum(1 for line in j.log if line.lstrip().startswith('✓') or '✓ ' in line)
    progress = 0.0
    if total > 0:
        progress = round(min(done_count, total) / total * 100.0, 2)
    bao_cao = j.ket_qua.get('bao_cao', []) if isinstance(j.ket_qua, dict) else []
    so_ok = sum(1 for x in bao_cao if x.get('ok'))
    so_giu = sum(1 for x in bao_cao if x.get('ly_do_xuat') == 'fallback_goc_do_fail_hau_kiem' or not x.get('ok'))
    return {
        'ma_job': j.ma_job,
        'trang_thai': j.trang_thai,
        'ten_file': j.ket_qua.get('ten_file') if isinstance(j.ket_qua, dict) else None,
        'so_file': total,
        'hau_kiem': {'tong': len(bao_cao), 'ok': so_ok, 'giu_nguyen': so_giu},
        'progress': {
            'current': min(done_count, total),
            'total': total,
            'percent': progress,
            'current_file': next((line.replace('  ✓ ', '') for line in reversed(j.log) if '✓' in line), None),
        },
        'gofile_link': j.ket_qua.get('gofile_link') if isinstance(j.ket_qua, dict) else None,
        'file_ket_qua': j.ket_qua.get('file_ket_qua') if isinstance(j.ket_qua, dict) else None,
        'log': j.log[-120:],
    }


def _settings_snapshot() -> SettingsData:
    gemini_model = ''
    gemini_workers = 4
    gg_workers = getattr(_router.gg, 'gg_workers', 40) if hasattr(_router, 'gg') else 40
    gemini_chunk_chars = 5000
    gg_chunk_chars = getattr(_router.gg, 'gg_chunk_chars', 700) if hasattr(_router, 'gg') else 700
    fallback_enabled = True
    gofile_upload = True
    if hasattr(_router, 'gemini') and hasattr(_router.gemini, 'get_current_model'):
        try:
            gemini_model = _router.gemini.get_current_model() or ''
        except Exception:
            gemini_model = ''
    keys = getattr(_router.gemini, 'keys', []) if hasattr(_router, 'gemini') else []
    preview = None
    if keys:
        k = keys[0]
        preview = k[:6] + '...' + k[-4:] if len(k) > 12 else k
    return SettingsData(
        source_lang=getattr(cai_dat_mac_dinh, 'default_source_lang', 'auto'),
        target_lang=getattr(cai_dat_mac_dinh, 'default_target_lang', 'vi'),
        gemini_model=gemini_model or getattr(cai_dat_mac_dinh, 'gemini_models', ['gemini-3.1-flash-lite-preview'])[0],
        gemini_workers=gemini_workers,
        gg_workers=gg_workers,
        gemini_chunk_chars=gemini_chunk_chars,
        gg_chunk_chars=gg_chunk_chars,
        fallback_enabled=fallback_enabled,
        gofile_upload=gofile_upload,
        api_key_enabled=bool(keys),
        api_key_preview=preview,
    )




def _tao_duong_dan_debug_tu_ten(ten_file: str, nhan: str) -> str:
    return f"__debug__/{ten_file}.{nhan}"


def _luu_hien_truong_api(ten_file: str, noi_dung_goc: str, ban_dich_raw: str, ban_an_toan: str, rpt: dict | None, kt_raw: dict, kt_safe: dict) -> dict[str, str]:
    p_orig = _lap.luu_text(_tao_duong_dan_debug_tu_ten(ten_file, 'orig'), noi_dung_goc)
    p_raw = _lap.luu_text(_tao_duong_dan_debug_tu_ten(ten_file, 'raw_out'), ban_dich_raw)
    p_safe = _lap.luu_text(_tao_duong_dan_debug_tu_ten(ten_file, 'safe_out'), ban_an_toan)
    report_data = {
        'file': ten_file,
        'trace_id': rpt.get('trace_id') if isinstance(rpt, dict) else None,
        'trace_file': rpt.get('trace_file') if isinstance(rpt, dict) else None,
        'nguon': rpt.get('nguon') if isinstance(rpt, dict) else None,
        'ban_xuat_de_xuat_la_goc': bool(rpt.get('can_xuat_goc')) if isinstance(rpt, dict) else False,
        'hau_kiem_raw': kt_raw,
        'hau_kiem_safe': kt_safe,
    }
    p_report = _lap.luu_text(_tao_duong_dan_debug_tu_ten(ten_file, 'report.json'), json.dumps(report_data, ensure_ascii=False, indent=2))
    return {'orig': str(p_orig), 'raw': str(p_raw), 'safe': str(p_safe), 'report': str(p_report)}

def _read_prompt() -> str:
    try:
        return PROMPT_FILE.read_text(encoding='utf-8')
    except Exception:
        return ''


def _write_prompt(text: str):
    PROMPT_FILE.write_text(text, encoding='utf-8')


async def _dich_3_vong_api(noi_dung: str, ten_file: str, lang_from: str, lang_to: str, loai: str):
    last_ban, last_rpt = noi_dung, {}
    lich_su = []
    for mode in AUTO_MODES:
        ban_dich, rpt = await _router.dich(noi_dung, ten_file, lang_from, lang_to, loai, mode=mode)
        rpt = rpt or {}
        rpt['mode'] = mode
        hk = rpt.get('hau_kiem') or {}
        fail_count = len(hk.get('loi', []) or []) if not hk.get('hop_le', True) else 0
        lich_su.append({'mode': mode, 'fail_count': fail_count, 'hop_le': bool(hk.get('hop_le', True))})
        last_ban, last_rpt = ban_dich, rpt
        if hk.get('hop_le', True):
            break
    last_rpt['lich_su_pass'] = lich_su
    return last_ban, last_rpt


@app.get('/', include_in_schema=False)
async def panel():
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return HTMLResponse('<h1>Thiếu file giao_tiep/web/index.html</h1>', status_code=500)


@app.get('/panel', include_in_schema=False)
async def panel_alias():
    return RedirectResponse(url='/', status_code=307)


@app.get('/api/health')
@app.get('/api/system/health')
async def health():
    return _ok({'status': 'healthy', 'version': cai_dat_mac_dinh.bot_version}, 'healthy')


@app.get('/api/system/info')
async def system_info():
    gem_keys = []
    gem_model = 'gemini-2.5-flash'
    gem_avail = False
    if hasattr(_router, 'gemini'):
        gem_keys = getattr(_router.gemini, 'keys', []) or []
        gem_avail = bool(gem_keys)
        if hasattr(_router.gemini, 'get_current_model'):
            try:
                gem_model = _router.gemini.get_current_model() or gem_model
            except Exception:
                pass
    jobs = list(getattr(_ql, 'ds', {}).values())
    return _ok({
        'app': app.title,
        'version': app.version,
        'uptime_seconds': int(time.time()) - START_TS,
        'status': 'running',
        'docs': '/api/docs',
        'panel': '/',
        'engines': {
            'gemini': {
                'enabled': True,
                'available': gem_avail,
                'model': gem_model,
                'keys_loaded': len(gem_keys),
            },
            'gg': {
                'enabled': True,
                'available': True,
                'workers': getattr(_router.gg, 'gg_workers', 40),
            }
        },
        'jobs': {
            'running': sum(1 for j in jobs if j.trang_thai == 'running'),
            'queued': sum(1 for j in jobs if j.trang_thai == 'queued'),
            'done': sum(1 for j in jobs if j.trang_thai == 'done'),
            'failed': sum(1 for j in jobs if j.trang_thai in ('error', 'failed')),
        }
    })


@app.get('/api/system/status')
async def system_status():
    return await system_info()


@app.get('/api/system/engines')
async def system_engines():
    info = (await system_info()).data
    return _ok(info.get('engines', {}))


@app.get('/api/languages')
async def lay_ngon_ngu():
    return _ok(bo_nhan_dien_ngon_ngu.lay_tat_ca())


@app.get('/api/stats')
async def thong_ke():
    stats = _router.gemini.thong_ke() if hasattr(_router, 'gemini') else {}
    return _ok(stats)


@app.get('/api/settings')
async def settings_get():
    return _ok(_settings_snapshot().model_dump())


@app.post('/api/settings/update')
async def settings_update(body: SettingsUpdateRequest):
    # Chỉ cập nhật mềm trên object hiện có, không phá flow cũ.
    for k, v in body.model_dump(exclude_none=True).items():
        if hasattr(cai_dat_mac_dinh, k):
            setattr(cai_dat_mac_dinh, k, v)
    return _ok(_settings_snapshot().model_dump(), 'settings_updated')


@app.post('/api/settings/reload')
async def settings_reload():
    # Không reset router để tránh đổi hành vi cũ; chỉ trả snapshot mới nhất.
    return _ok({'reloaded': True, 'settings': _settings_snapshot().model_dump()}, 'settings_reloaded')


@app.get('/api/gemini/status')
async def gemini_status():
    keys = getattr(_router.gemini, 'keys', []) if hasattr(_router, 'gemini') else []
    model = 'gemini-2.5-flash'
    if hasattr(_router, 'gemini') and hasattr(_router.gemini, 'get_current_model'):
        try:
            model = _router.gemini.get_current_model() or model
        except Exception:
            pass
    return _ok({'model': model, 'keys_loaded': len(keys), 'available': bool(keys)})


@app.get('/api/gemini/prompt')
async def gemini_prompt_get():
    return _ok({'prompt': _read_prompt()})


@app.post('/api/gemini/prompt')
async def gemini_prompt_set(body: GeminiPromptUpdateRequest):
    _write_prompt(body.prompt)
    return _ok({'prompt': body.prompt}, 'prompt_saved')


@app.get('/api/plugins/list')
@app.get('/api/plugins')
async def list_plugins():
    return _ok({
        'ds': _plugins.tat_ca_plugin_can_dao(),
        'bo_qua': _plugins.plugin_bo_qua(),
    })


@app.get('/api/plugins/defaults')
async def plugin_defaults():
    return _ok({
        'nen_dao': _plugins.plugin_mac_dinh_nen_dao(),
        'can_than': _plugins.plugin_mac_dinh_can_than(),
        'bo_qua': _plugins.plugin_bo_qua(),
    })


@app.post('/api/plugins/scan')
async def scan_plugins(file: UploadFile = File(...)):
    ten_safe = _safe_name(file.filename)
    duong_dan = thu_muc_tam / ten_safe
    duong_dan.write_bytes(await file.read())
    ket_qua = _quet_ng.quet(duong_dan)
    return _ok({'ten_file': ten_safe, 'scan_ngoai': ket_qua})


@app.post('/api/plugins/luu')
async def luu_plugins(plugin_da_chon: str = Form(...)):
    ds = [x.strip() for x in plugin_da_chon.split(',') if x.strip()]
    for p in ds:
        _plugins.them_plugin(p)
    return _ok({'da_luu': ds, 'tat_ca': _plugins.tat_ca_plugin_can_dao()}, 'plugins_saved')


@app.post('/api/plugins/them')
async def them_plugin(body: PluginModifyRequest):
    _plugins.them_plugin(body.ten)
    return _ok({'ds': _plugins.tat_ca_plugin_can_dao()}, 'plugin_added')


@app.post('/api/plugins/xoa')
async def xoa_plugin(body: PluginModifyRequest):
    _plugins.xoa_plugin(body.ten)
    return _ok({'ds': _plugins.tat_ca_plugin_can_dao()}, 'plugin_removed')


@app.get('/api/keys')
async def lay_keys():
    keys = getattr(_router.gemini, 'keys', []) if hasattr(_router, 'gemini') else []
    statuses = getattr(_router.gemini, 'key_status', {}) if hasattr(_router, 'gemini') else {}
    result = []
    for k in keys:
        st = statuses.get(k, {}) if isinstance(statuses, dict) else {}
        result.append({
            'key': k,
            'status': st.get('status', 'active'),
            'model': st.get('model', ''),
        })
    return _ok({'keys': result})


class ThemKeyBody(PluginModifyRequest):
    pass


@app.post('/api/keys')
async def them_key(body: ThemKeyBody):
    key = body.ten.strip()
    if not key:
        _err('invalid_request', 'Key rỗng')
    if hasattr(_router, 'gemini') and hasattr(_router.gemini, 'them_key'):
        _router.gemini.them_key(key)
    if hasattr(cai_dat_mac_dinh, 'gemini_api_keys'):
        cai_dat_mac_dinh.gemini_api_keys.append(key)
    return _ok({'tong_key': len(getattr(_router.gemini, 'keys', []))}, 'key_added')


@app.post('/api/translate/text')
async def translate_text(body: TranslateTextRequest):
    loai = body.file_type if body.file_type != 'auto' else 'text'
    ban_dich, rpt = await _dich_3_vong_api(body.text, 'api_text', body.source_lang, body.target_lang, loai)
    return _ok({'engine': rpt.get('nguon', 'unknown') if isinstance(rpt, dict) else 'unknown', 'result': ban_dich, 'debug': rpt if body.return_debug else None}, 'translated')


@app.post('/api/translate/file')
async def translate_file(body: TranslateFileRequest):
    path = Path(body.path)
    if not path.exists():
        _err('not_found', 'Không tìm thấy file/path', str(path), 404)
    selected = body.selected_plugins if body.scan_mode == 'selected_plugins' else None
    scan = _quet.quet(path, ds_plugin_can_dao=selected)
    j = _ql.tao_job()
    j.ket_qua.update({'scan': scan, 'ten_file': path.name, 'duong_dan': str(path)})
    j.trang_thai = 'queued'
    j.log.append(f'Upload: {path.name} | Cần dịch: {len(scan["can_dich"])} file')
    return _ok({'ma_job': j.ma_job, 'status': 'queued', 'scan': scan}, 'job_created')


@app.post('/api/jobs/upload')
async def upload(file: UploadFile = File(...), plugin_da_chon: str = Form(default='')):
    noi_dung = await file.read()
    if len(noi_dung) > cai_dat_mac_dinh.max_file_size_mb * 1024 * 1024:
        _err('invalid_request', f'File quá lớn (tối đa {cai_dat_mac_dinh.max_file_size_mb}MB)', status_code=413)
    ten_safe = _safe_name(file.filename)
    duong_dan = thu_muc_tam / ten_safe
    duong_dan.write_bytes(noi_dung)
    ds_plugin = [x.strip() for x in plugin_da_chon.split(',') if x.strip()]
    scan = _quet.quet(duong_dan, ds_plugin_can_dao=ds_plugin if ds_plugin else None)
    j = _ql.tao_job()
    j.ket_qua.update({'scan': scan, 'ten_file': ten_safe, 'duong_dan': str(duong_dan)})
    j.trang_thai = 'queued'
    j.log.append(f'Upload: {ten_safe} | Cần dịch: {len(scan["can_dich"])} file')
    log.info(f'Job {j.ma_job} tao tu {ten_safe}')
    return _ok({'ma_job': j.ma_job, 'scan': scan}, 'uploaded')


@app.get('/api/jobs')
async def ds_jobs(limit: int = Query(50, ge=1, le=500), status: str | None = None, offset: int = Query(0, ge=0)):
    ds = list(_ql.ds.values())
    if status:
        ds = [j for j in ds if j.trang_thai == status]
    total = len(ds)
    ds = ds[max(0, total - offset - limit): total - offset if offset else None]
    items = [_serialize_job(j) for j in reversed(ds)]
    return _ok({'items': items, 'total': total})


@app.get('/api/jobs/list')
async def ds_jobs_alias(limit: int = Query(50, ge=1, le=500), status: str | None = None, offset: int = Query(0, ge=0)):
    return await ds_jobs(limit, status, offset)


@app.get('/api/jobs/recent')
async def ds_jobs_recent(limit: int = Query(20, ge=1, le=100)):
    return await ds_jobs(limit)


@app.get('/api/jobs/summary')
async def jobs_summary():
    ds = list(_ql.ds.values())
    return _ok({
        'tong': len(ds),
        'queued': sum(1 for j in ds if j.trang_thai == 'queued'),
        'running': sum(1 for j in ds if j.trang_thai == 'running'),
        'done': sum(1 for j in ds if j.trang_thai == 'done'),
        'error': sum(1 for j in ds if j.trang_thai == 'error'),
    })


@app.get('/api/jobs/{ma_job}')
async def trang_thai_job(ma_job: str):
    j = _ql.lay_job(ma_job)
    if not j:
        _err('not_found', f'Không tìm thấy job {ma_job}', status_code=404)
    return _ok(_serialize_job(j))


@app.get('/api/jobs/{ma_job}/logs')
async def logs_job(ma_job: str):
    j = _ql.lay_job(ma_job)
    if not j:
        _err('not_found', 'Không tìm thấy job', status_code=404)
    return _ok({'logs': j.log[-200:]})


@app.get('/api/jobs/{ma_job}/result')
async def result_job(ma_job: str):
    j = _ql.lay_job(ma_job)
    if not j:
        _err('not_found', 'Không tìm thấy job', status_code=404)
    return _ok({
        'ma_job': j.ma_job,
        'status': j.trang_thai,
        'result_path': j.ket_qua.get('file_ket_qua'),
        'gofile_link': j.ket_qua.get('gofile_link'),
        'bao_cao': j.ket_qua.get('bao_cao', []),
    })


@app.post('/api/jobs/{ma_job}/run')
async def chay_dich(ma_job: str, body: RunBody):
    j = _ql.lay_job(ma_job)
    if not j:
        _err('not_found', 'Không tìm thấy job', status_code=404)
    if j.trang_thai == 'running':
        _err('invalid_request', 'Job đang chạy', status_code=409)
    j.trang_thai = 'running'
    j.log.append(f'Bắt đầu: {body.lang_from} → {body.lang_to}')
    asyncio.create_task(_pipeline(j, body.lang_from, body.lang_to))
    return _ok({'ma_job': j.ma_job, 'trang_thai': 'running'}, 'job_running')


@app.post('/api/jobs/{ma_job}/cancel')
async def cancel_job(ma_job: str):
    j = _ql.lay_job(ma_job)
    if not j:
        _err('not_found', 'Không tìm thấy job', status_code=404)
    j.ket_qua['cancelled'] = True
    j.trang_thai = 'cancelled'
    j.log.append('⚠ Job bị huỷ')
    return _ok({'ma_job': j.ma_job, 'trang_thai': 'cancelled'}, 'job_cancelled')


@app.post('/api/jobs/{ma_job}/retry')
async def retry_job(ma_job: str):
    j = _ql.lay_job(ma_job)
    if not j:
        _err('not_found', 'Không tìm thấy job', status_code=404)
    if j.trang_thai == 'running':
        _err('invalid_request', 'Job đang chạy', status_code=409)
    j.ket_qua['cancelled'] = False
    j.trang_thai = 'queued'
    j.log.append('↻ Đánh dấu chạy lại')
    return _ok({'ma_job': j.ma_job, 'trang_thai': 'queued'}, 'job_retried')


@app.delete('/api/jobs/{ma_job}')
async def delete_job(ma_job: str):
    if ma_job in _ql.ds:
        del _ql.ds[ma_job]
    return _ok({'ma_job': ma_job, 'action': 'deleted'}, 'job_deleted')


async def _pipeline(j: job, lang_from: str, lang_to: str):
    try:
        duong_dan = Path(j.ket_qua['duong_dan'])
        scan = j.ket_qua['scan']
        ds = scan.get('can_dich', [])
        out_files: list[tuple[Path, str]] = []
        bao_cao_data = []

        if scan.get('archive'):
            for ten in ds:
                if j.ket_qua.get('cancelled'):
                    j.log.append('⚠ Dừng pipeline vì job đã bị huỷ')
                    break
                try:
                    noi_dung = _trich.doc_trong_zip(duong_dan, ten)
                    loai = _phanloai.lay_loai(ten) or 'text'
                    ban_dich, rpt = await _dich_3_vong_api(noi_dung, ten, lang_from, lang_to, loai)
                    kt_raw = _valid.kiem_tra(noi_dung, ban_dich)
                    ban_xuat = rpt.get('ban_xuat_de_xuat', ban_dich) if isinstance(rpt, dict) else ban_dich
                    kt_safe = _valid.kiem_tra(noi_dung, ban_xuat)
                    bao_cao_item = {
                        'file': ten,
                        'nguon': rpt.get('nguon') if isinstance(rpt, dict) else None,
                        'ok': kt_safe['hop_le'],
                        'loi': kt_safe.get('loi', []),
                        'loi_raw': kt_raw.get('loi', []),
                        'trace_id': rpt.get('trace_id') if isinstance(rpt, dict) else None,
                        'trace_file': rpt.get('trace_file') if isinstance(rpt, dict) else None,
                        'ly_do_xuat': 'ban_an_toan' if kt_safe.get('hop_le') else 'ban_an_toan_fail',
                    }
                    bao_cao_data.append(bao_cao_item)
                    out_path = _lap.luu_text(f'{j.ma_job}/{ten}', ban_xuat)
                    debug_paths = _luu_hien_truong_api(f'{j.ma_job}/{ten}', noi_dung, ban_dich, ban_xuat, rpt or {}, kt_raw, kt_safe)
                    out_files.append((out_path, ten))
                    out_files.append((Path(debug_paths['orig']), f'__debug__/{ten}.orig'))
                    out_files.append((Path(debug_paths['raw']), f'__debug__/{ten}.raw_out'))
                    out_files.append((Path(debug_paths['safe']), f'__debug__/{ten}.safe_out'))
                    out_files.append((Path(debug_paths['report']), f'__debug__/{ten}.report.json'))
                    j.log.append(f"  ⇢ {ten} trace={bao_cao_item['trace_id'] or '?'}")
                    j.log.append(f"    send/recv log: {bao_cao_item['trace_file'] or '?'}")
                    trang_thai_item = 'OK' if bao_cao_item['ok'] else 'GIU_GOC'
                    j.log.append(f"  ✓ {ten} [{bao_cao_item['nguon'] or '?'}] {trang_thai_item}")
                except Exception as e:
                    j.log.append(f'  ✗ {ten}: {e}')
            if out_files and not j.ket_qua.get('cancelled'):
                zip_out = thu_muc_ket_qua / f'{j.ma_job}.zip'
                with zipfile.ZipFile(zip_out, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for p, arc in out_files:
                        zf.write(p, arcname=arc)
                j.ket_qua['file_ket_qua'] = str(zip_out)
        else:
            if ds and not j.ket_qua.get('cancelled'):
                ten = ds[0]
                noi_dung = _trich.doc_file(duong_dan)
                loai = _phanloai.lay_loai(ten) or 'text'
                ban_dich, rpt = await _dich_3_vong_api(noi_dung, ten, lang_from, lang_to, loai)
                kt_raw = _valid.kiem_tra(noi_dung, ban_dich)
                ban_xuat = rpt.get('ban_xuat_de_xuat', ban_dich) if isinstance(rpt, dict) else ban_dich
                kt_safe = _valid.kiem_tra(noi_dung, ban_xuat)
                bao_cao_item = {
                    'file': ten,
                    'nguon': rpt.get('nguon') if isinstance(rpt, dict) else None,
                    'ok': kt_safe['hop_le'],
                    'loi': kt_safe.get('loi', []),
                    'loi_raw': kt_raw.get('loi', []),
                    'trace_id': rpt.get('trace_id') if isinstance(rpt, dict) else None,
                    'trace_file': rpt.get('trace_file') if isinstance(rpt, dict) else None,
                    'ly_do_xuat': 'ban_an_toan' if kt_safe.get('hop_le') else 'ban_an_toan_fail',
                }
                bao_cao_data.append(bao_cao_item)
                ten_out = f'{Path(ten).stem}_translated{Path(ten).suffix}'
                out_path = _lap.luu_text(ten_out, ban_xuat)
                _luu_hien_truong_api(ten_out, noi_dung, ban_dich, ban_xuat, rpt or {}, kt_raw, kt_safe)
                j.ket_qua['file_ket_qua'] = str(out_path)
                j.log.append(f"  ⇢ {ten} trace={bao_cao_item['trace_id'] or '?'}")
                j.log.append(f"    send/recv log: {bao_cao_item['trace_file'] or '?'}")
                trang_thai_item = 'OK' if bao_cao_item['ok'] else 'GIU_GOC'
                j.log.append(f"  ✓ {ten} [{bao_cao_item['nguon'] or '?'}] {trang_thai_item}")

        j.ket_qua['bao_cao'] = bao_cao_data
        if not j.ket_qua.get('cancelled'):
            file_ket_qua = j.ket_qua.get('file_ket_qua')
            if file_ket_qua:
                try:
                    ket_qua_tai = await _uploader.tai_len(Path(file_ket_qua))
                    if ket_qua_tai.get('link'):
                        j.ket_qua['gofile_link'] = ket_qua_tai['link']
                        j.log.append(f"🌐 Gofile: {ket_qua_tai['link']}")
                except Exception as e:
                    j.log.append(f'⚠ Không upload được Gofile: {e}')
            _reporter.luu(j.ma_job, {'job': j.ma_job, 'files': bao_cao_data})
            j.trang_thai = 'done'
            so_ok = sum(1 for x in bao_cao_data if x.get('ok'))
            j.log.append(f'✅ Xong! {len(bao_cao_data)} file | hậu kiểm ok {so_ok}/{len(bao_cao_data)}')
    except Exception as e:
        j.trang_thai = 'error'
        j.log.append(f'❌ LỖI: {e}')
        log.error(f'Job {j.ma_job} lỗi: {e}')


@app.get('/api/jobs/{ma_job}/download')
async def tai_ket_qua(ma_job: str):
    j = _ql.lay_job(ma_job)
    if not j:
        _err('not_found', 'Không tìm thấy job', status_code=404)
    if j.trang_thai != 'done':
        _err('job_not_ready', f'Job chưa xong ({j.trang_thai})', status_code=425)
    path = j.ket_qua.get('file_ket_qua')
    if not path or not Path(path).exists():
        _err('not_found', 'File kết quả không tồn tại', status_code=404)
    return FileResponse(path, filename=Path(path).name)


@app.get('/api/jobs/{ma_job}/gofile')
async def lay_gofile_job(ma_job: str):
    j = _ql.lay_job(ma_job)
    if not j:
        _err('not_found', 'Không tìm thấy job', status_code=404)
    return _ok({'ma_job': ma_job, 'gofile_link': j.ket_qua.get('gofile_link')})


@app.get('/api/cache/summary')
async def cache_summary():
    from cau_hinh.hang_so import thu_muc_tri_nho
    data = {
        'bo_nho_dich_entries': len(_doc_json(Path(thu_muc_tri_nho / 'bo_nho_dich.json'), {})),
        'diff_hoc_entries': len(_doc_json(Path(thu_muc_tri_nho / 'diff_hoc.json'), {}).get('term', {})),
    }
    return _ok(data)


@app.get('/api/shield/data')
async def shield_data():
    dl = getattr(_router.gg, 'du_lieu', None)
    if dl and not getattr(dl, '_da_nap', False):
        dl.nap()
    return _ok({
        'default_keys_translate': sorted(list(dl.du_lieu.get('key_dich', [])))[:120] if dl else [],
        'default_keys_block': sorted(list(dl.du_lieu.get('key_cam', [])))[:120] if dl else [],
        'custom_loaded_files': [str(dl.file_common)] if dl else [],
    })


@app.post('/api/shield/check')
async def shield_check(body: ShieldCheckRequest):
    text = body.text.strip()
    key = ''
    parent = body.parent or ''
    action = 'giu_nguyen'
    reason = 'unknown'
    if ':' in text:
        key = text.split(':', 1)[0].strip().strip('"\'')
        key_norm = ''.join(ch.lower() for ch in key if ch.isalnum())
        dich = {'displayname', 'displayname', 'menutitle', 'title', 'subtitle', 'description', 'message', 'messages', 'text', 'content', 'status', 'available', 'lore'}
        cam = {'permission', 'permissions', 'material', 'slot', 'slots', 'priority', 'amount', 'size', 'type', 'cooldown', 'command', 'commands', 'opencommand', 'opencommands', 'clickcommands', 'leftclickcommands', 'rightclickcommands', 'consolecommands', 'playercommands', 'requirements', 'viewrequirement', 'input', 'output'}
        if key_norm in dich:
            action = 'dich_gg'
            reason = 'default_key_translate'
        elif key_norm in cam:
            action = 'cam'
            reason = 'default_key_block'
        else:
            action = 'cho_data'
            reason = 'missing_rule'
    return _ok({'action': action, 'key': key or None, 'parent': parent, 'path': body.path or '', 'safe': action == 'dich_gg', 'reason': reason}, 'classified')


@app.post('/panel/scan', response_class=HTMLResponse)
async def panel_scan_legacy(file: UploadFile = File(...)):
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return HTMLResponse('<h1>Thiếu file panel</h1>', status_code=500)
