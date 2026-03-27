"""Helper tối giản cho web panel tách file ngoài."""
from pathlib import Path


THU_MUC_WEB = Path(__file__).resolve().parent / 'web'
INDEX_HTML = THU_MUC_WEB / 'index.html'
PANEL_CSS = THU_MUC_WEB / 'panel.css'
PANEL_JS = THU_MUC_WEB / 'panel.js'


def duong_dan_panel() -> Path:
    return INDEX_HTML


def tao_trang_chu_panel(*_args, **_kwargs) -> str:
    if INDEX_HTML.exists():
        return INDEX_HTML.read_text(encoding='utf-8')
    return '<h1>Thiếu file giao_tiep/web/index.html</h1>'
