from dataclasses import dataclass, field
from typing import List
import os
from pathlib import Path


def _nap_env(force: bool = True):
    env_file = Path(__file__).resolve().parents[1] / '.env'
    if env_file.exists():
        for dong in env_file.read_text(encoding='utf-8').splitlines():
            dong = dong.strip()
            if dong and not dong.startswith('#') and '=' in dong:
                k, _, v = dong.partition('=')
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if force:
                    os.environ[k] = v
                else:
                    os.environ.setdefault(k, v)




def _doc_bool(name: str, default: bool) -> bool:
    _nap_env(force=True)
    raw = str(os.environ.get(name, str(default))).strip().lower()
    if raw in {'1', 'true', 'yes', 'on'}:
        return True
    if raw in {'0', 'false', 'no', 'off'}:
        return False
    return default




def _doc_int(name: str, default: int) -> int:
    _nap_env(force=True)
    raw = str(os.environ.get(name, str(default))).strip()
    try:
        return int(raw)
    except Exception:
        return default


def _doc_float(name: str, default: float) -> float:
    _nap_env(force=True)
    raw = str(os.environ.get(name, str(default))).strip()
    try:
        return float(raw)
    except Exception:
        return default



def _doc_list(name: str, default: list[str]) -> List[str]:
    _nap_env(force=True)
    raw = str(os.environ.get(name, '')).strip()
    if not raw:
        return list(default)
    out = [x.strip() for x in raw.split(',') if x.strip()]
    return out or list(default)

def _doc_keys() -> List[str]:
    _nap_env(force=True)
    nhieu = os.environ.get('GEMINI_API_KEYS', '').strip()
    if nhieu:
        return [k.strip() for k in nhieu.split(',') if k.strip() and not k.strip().startswith('YOUR_')]
    mot = os.environ.get('GEMINI_API_KEY', '').strip()
    if mot and not mot.startswith('YOUR_'):
        return [mot]
    return []


@dataclass
class cai_dat_he_thong:
    bot_version: str = '3.1.0'
    api_timeout: int = 300
    max_retries: int = 5
    delay_giua_request: int = 2
    max_file_size_mb: int = 50
    max_files_moi_yeu_cau: int = 20
    max_concurrent_users: int = 3
    max_concurrent_files: int = 5
    chunk_size: int = 20
    feedback_timeout: int = 120
    enable_cache: bool = True
    enable_smart_filter: bool = True
    default_source_lang: str = 'auto'
    default_target_lang: str = 'vi'
    exponential_backoff_base: int = 2
    max_backoff_time: int = 60
    gemini_api_keys: List[str] = field(default_factory=_doc_keys)
    gemini_models: List[str] = field(default_factory=lambda: [
        'gemini-3.1-flash-lite-preview',
        'gemini-3-flash-preview',
        'gemini-3.1-pro-preview',
        'gemini-2.5-flash',
    ])
    use_gemini: bool = field(default_factory=lambda: _doc_bool('USE_GEMINI', True))
    use_gg: bool = field(default_factory=lambda: _doc_bool('USE_GG', True))
    learn_from_gemini: bool = field(default_factory=lambda: _doc_bool('LEARN_FROM_GEMINI', True))
    save_fail_artifacts: bool = field(default_factory=lambda: _doc_bool('SAVE_FAIL_ARTIFACTS', True))
    gg_workers: int = field(default_factory=lambda: _doc_int('GG_WORKERS', 8))
    gg_min_concurrency: int = field(default_factory=lambda: _doc_int('GG_MIN_CONCURRENCY', 2))
    gg_max_concurrency: int = field(default_factory=lambda: _doc_int('GG_MAX_CONCURRENCY', 6))
    gg_chunk_chars: int = field(default_factory=lambda: _doc_int('GG_CHUNK_CHARS', 1200))
    gg_requests_per_second: float = field(default_factory=lambda: _doc_float('GG_REQUESTS_PER_SECOND', 2.2))
    gg_retry_count: int = field(default_factory=lambda: _doc_int('GG_RETRY_COUNT', 2))
    gg_retry_base_seconds: float = field(default_factory=lambda: _doc_float('GG_RETRY_BASE_SECONDS', 1.25))
    gg_retry_max_seconds: float = field(default_factory=lambda: _doc_float('GG_RETRY_MAX_SECONDS', 8.0))
    gg_fragment_cache_size: int = field(default_factory=lambda: _doc_int('GG_FRAGMENT_CACHE_SIZE', 10000))
    gg_endpoints: List[str] = field(default_factory=lambda: _doc_list('GG_ENDPOINTS', [
        'https://translate.googleapis.com/translate_a/single',
        'https://translate.google.com/translate_a/single',
        'https://translate.google.com.vn/translate_a/single',
    ]))
    gg_backend_timeout_ms: int = field(default_factory=lambda: _doc_int('GG_BACKEND_TIMEOUT_MS', 2500))
    gg_backend_max_fail: int = field(default_factory=lambda: _doc_int('GG_BACKEND_MAX_FAIL', 3))
    gg_backend_cooldown_sec: int = field(default_factory=lambda: _doc_int('GG_BACKEND_COOLDOWN_SEC', 60))


cai_dat_mac_dinh = cai_dat_he_thong()
