import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from cau_hinh.hang_so import thu_muc_log


_console_emitter: Callable[[str], None] | None = None
_console_enabled: bool = False


def bat_console_trace(emitter: Callable[[str], None] | None = None, enabled: bool = True):
    global _console_emitter, _console_enabled
    _console_emitter = emitter
    _console_enabled = enabled and emitter is not None


def tat_console_trace():
    global _console_emitter, _console_enabled
    _console_emitter = None
    _console_enabled = False


def _fmt_console(rec: dict[str, Any]) -> str:
    stage = rec.get('stage', '?').upper()
    file = rec.get('file') or rec.get('ten_file') or ''
    line_idx = rec.get('line_idx')
    path = rec.get('path') or ''
    dang_lam = rec.get('dang_lam') or ''
    parts = [f"[bold #00ffff]{stage}[/]"]
    if file:
        parts.append(f"[white]{file}[/]")
    if line_idx is not None:
        parts.append(f"[dim]L{line_idx}[/]")
    if path:
        parts.append(f"[magenta]{path}[/]")
    if dang_lam:
        parts.append(f"[dim]- {dang_lam}[/]")
    head = ' '.join(parts)

    payload = []
    order = [
        ('raw', 'raw'), ('value_goc', 'value'), ('prefix', 'prefix'), ('text', 'text'), ('suffix', 'suffix'),
        ('truoc', 'truoc'), ('sau', 'sau'), ('text_goc', 'goc'), ('text_gui_di', 'gui'), ('text_tra_ve', 'tra'),
        ('text_sau_mo', 'mo'), ('text_xuat', 'xuat'), ('action', 'action'), ('ly_do', 'ly_do'), ('error', 'loi'),
        ('errors', 'errors'), ('ok', 'ok')
    ]
    for key, label in order:
        if key in rec and rec.get(key) not in (None, '', [], {}):
            payload.append(f"  [bold white]{label}[/]: {rec.get(key)}")
    return head + ('\n' + '\n'.join(payload) if payload else '')


def tao_logger(ten: str = 'he_thong_dich'):
    logger = logging.getLogger(ten)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    dinh_dang = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

    stream = logging.StreamHandler()
    stream.setFormatter(dinh_dang)
    logger.addHandler(stream)

    file_handler = logging.FileHandler(thu_muc_log / 'he_thong.log', encoding='utf-8')
    file_handler.setFormatter(dinh_dang)
    logger.addHandler(file_handler)
    return logger


class trace_logger:
    def __init__(self, trace_id: str | None = None, thu_muc: Path | None = None):
        self.trace_id = trace_id or f'trace_{uuid.uuid4().hex[:12]}'
        self.thu_muc = Path(thu_muc or (thu_muc_log / 'trace'))
        self.thu_muc.mkdir(parents=True, exist_ok=True)
        self.duong_dan = self.thu_muc / f'{self.trace_id}.jsonl'
        self._lock = threading.Lock()

    def _rut_gon(self, data: Any, max_len: int = 4000):
        if data is None:
            return None
        if isinstance(data, (dict, list, tuple)):
            try:
                text = json.dumps(data, ensure_ascii=False)
            except Exception:
                text = repr(data)
        else:
            text = str(data)
        if len(text) <= max_len:
            return text
        return text[:max_len] + f'...<rut_gon {len(text) - max_len} ky tu>'

    def ghi(self, stage: str, **fields):
        rec = {
            'ts': datetime.utcnow().isoformat() + 'Z',
            'trace_id': self.trace_id,
            'stage': stage,
        }
        for k, v in fields.items():
            if k in {'input', 'output', 'raw', 'text_goc', 'text_gui_di', 'text_tra_ve', 'text_sau_mo', 'text_xuat', 'truoc', 'sau', 'value_goc', 'prefix', 'text', 'suffix'}:
                rec[k] = self._rut_gon(v)
            else:
                rec[k] = v
        line = json.dumps(rec, ensure_ascii=False)
        with self._lock:
            with self.duong_dan.open('a', encoding='utf-8') as f:
                f.write(line + '\n')
        if _console_enabled and _console_emitter is not None:
            try:
                _console_emitter(_fmt_console(rec))
            except Exception:
                pass

    def stage(self, stage: str, input: Any = None, output: Any = None, **fields):
        self.ghi(stage, input=input, output=output, **fields)

    def loi(self, stage: str, error: Any, **fields):
        self.ghi(stage, error=self._rut_gon(error, 2000), ok=False, **fields)


def tao_trace_logger(trace_id: str | None = None) -> trace_logger:
    return trace_logger(trace_id=trace_id)


log = tao_logger()
