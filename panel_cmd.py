#!/usr/bin/env python3
"""
╔══════════════════════════════════════════╗
║     PANEL CMD - HE THONG DICH v3.1.0    ║
║     Chon so de dieu huong menu           ║
╚══════════════════════════════════════════╝
Chay: python panel_cmd.py
"""
import sys, os, asyncio, time, json
from pathlib import Path

try:
    import yaml
except Exception:
    yaml = None

# --- THƯ VIỆN UI (RICH) ---
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import box
from rich.live import Live
from dieu_phoi.fallback_modes import AUTO_MODES, dem_fail as _dem_fail_report, can_hardcore as _can_hardcore_report

console = Console()
IS_BOOTED = False # Flag de chi hien animation 1 lan luc khoi dong

sys.path.insert(0, str(Path(__file__).parent))

# ─── Mau sac (Dùng cho core cũ nếu có) ─────────────────────────────
R  = '\033[0m'
B  = '\033[1m'
DIM= '\033[2m'
IT = '\033[3m'
G  = '\033[92m'   
Y  = '\033[93m'   
RE = '\033[91m'   
C  = '\033[96m'   
BL = '\033[94m'   
M  = '\033[95m'   
W  = '\033[97m'   

def _deep_merge(mac_dinh, moi):
    if not isinstance(mac_dinh, dict):
        return moi if moi is not None else mac_dinh
    out = dict(mac_dinh)
    if not isinstance(moi, dict):
        return out
    for k, v in moi.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def _cfg_panel_mac_dinh():
    return {
        'panel': {
            'tieu_de': 'HỆ THỐNG DỊCH AI',
            'phien_ban': 'v3.1.0',
            'dong_phu': 'Core: Gemini · Plugin-Aware',
            'bieu_tuong': '⚡',
        }
    }

def _duong_dan_cfg_panel() -> Path:
    return Path(__file__).parent / 'cau_hinh' / 'panel_cmd.yml'

def tao_cfg_panel_neu_thieu():
    p = _duong_dan_cfg_panel()
    if p.exists() or yaml is None:
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(_cfg_panel_mac_dinh(), allow_unicode=True, sort_keys=False), encoding='utf-8')

def nap_cfg_panel(force: bool = False):
    global CFG_PANEL
    if CFG_PANEL is not None and not force:
        return CFG_PANEL
    mac_dinh = _cfg_panel_mac_dinh()
    p = _duong_dan_cfg_panel()
    if yaml is None:
        CFG_PANEL = mac_dinh
        return CFG_PANEL
    if not p.exists():
        tao_cfg_panel_neu_thieu()
    try:
        data = yaml.safe_load(p.read_text(encoding='utf-8')) if p.exists() else {}
        CFG_PANEL = _deep_merge(mac_dinh, data or {})
    except Exception:
        CFG_PANEL = mac_dinh
    return CFG_PANEL

def cfg_panel(path: str, mac_dinh=None):
    data = nap_cfg_panel()
    cur = data
    for part in path.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return mac_dinh
        cur = cur[part]
    return cur

CFG_PANEL = None

# ─── HỆ THỐNG UI ANIMATION (CYBERPUNK) ─────────────────────────────

def clr():
    # Xoá triệt để Termux Scrollback
    print("\033c", end="")
    os.system('cls' if os.name == 'nt' else 'clear')
    console.clear()

def boot_animation():
    global IS_BOOTED
    if IS_BOOTED: return
    clr()
    # Hieu ung boot he thong
    with console.status("[bold #00ffff]⠋ Khởi động Hệ Thống Dịch AI...", spinner="dots12"):
        time.sleep(0.4)
        console.print("  [dim green]✔ Nạp lõi Gemini API[/]")
        time.sleep(0.3)
        console.print("  [dim green]✔ Khởi tạo Plugin Database[/]")
        time.sleep(0.3)
        console.print("  [dim green]✔ Sẵn sàng kết nối...[/]")
        time.sleep(0.4)
    IS_BOOTED = True
    clr()

def banner(sub: str = ''):
    tieu_de = str(cfg_panel('panel.tieu_de', 'HỆ THỐNG DỊCH AI')).upper()
    phien_ban = str(cfg_panel('panel.phien_ban', 'v3.1.0'))
    dong_phu = str(cfg_panel('panel.dong_phu', 'Core: Gemini · Plugin-Aware'))
    
    t = Text(justify="center")
    t.append(f"{tieu_de} ", style="bold #00ffff") 
    t.append(f"[{phien_ban}]\n", style="bold #ff00ff")
    t.append(f"{dong_phu}", style="dim white")
    
    p = Panel(t, box=box.ROUNDED, border_style="#ff00ff", expand=False, padding=(1, 4))
    console.print(Align.center(p))
    if sub:
        console.print(f"[dim italic]   {sub}[/]\n", justify="center")
    else:
        console.print("\n")

def ok(msg):    console.print(f"  [bold green]✔[/] {msg}")
def warn(msg):  console.print(f"  [bold yellow]⚠[/] {msg}")
def err(msg):   console.print(f"  [bold red]✖[/] {msg}")
def info(msg):  console.print(f"  [bold cyan]ℹ[/] {msg}")

def nhap(prompt: str, mac_dinh: str = '') -> str:
    # Giao dien nhap lieu gon gang
    console.print(f"  [bold #00ffff]◆[/] [white]{prompt}[/]")
    if mac_dinh:
        val = input(f"  \033[95m╰─➤\033[0m [\033[90m{mac_dinh}\033[0m]: ").strip()
        return val or mac_dinh
    return input(f"  \033[95m╰─➤\033[0m ").strip()

def chon(prompt: str, ds: list, mac_dinh: str = '') -> str:
    console.print()
    tb = Table(box=None, show_header=False, padding=(0, 2))
    for i, x in enumerate(ds, 1):
        tb.add_row(f"[bold #ff00ff]{i:>2}[/]", f"[white]{x}[/]")
    console.print(tb)
    console.print()
    
    while True:
        val = nhap(prompt, mac_dinh)
        if val.isdigit() and 1 <= int(val) <= len(ds):
            return ds[int(val) - 1]
        if val in ds:
            return val
        err(f'Chọn từ 1 đến {len(ds)}')

def menu(tieu_de: str, muc: list[tuple[str,str]]) -> str:
    console.print(f"  [bold white]{tieu_de}[/]")
    console.print("  [dim]──────────────────────────────────────[/]")
    
    tb = Table(box=None, show_header=False, padding=(0, 2))
    for key, mo_ta in muc:
        tb.add_row(f"[bold #00ffff]{key:>2}[/]", f"[white]{mo_ta}[/]")
    console.print(tb)
    console.print("  [dim]──────────────────────────────────────[/]\n")
    
    while True:
        val = input(f"  \033[95m❯ \033[0m").strip()
        for key, _ in muc:
            if val == key:
                return val
        err("Nhập số hợp lệ trong menu")


# ─── Lazy load modules ─────────────────────────────────────────────
_router = None
_tri_nho_plugin = None
_du_lieu_gg = None

def _get_router():
    global _router
    if _router is None:
        from loi.bo_dinh_tuyen_dich import bo_dinh_tuyen_dich
        from cau_hinh.cai_dat import cai_dat_he_thong
        _router = bo_dinh_tuyen_dich(cai_dat_he_thong())
    return _router

def _get_plugin_data():
    global _tri_nho_plugin
    if _tri_nho_plugin is None:
        from tri_nho.du_lieu_plugin_can_dao import du_lieu_plugin_can_dao
        _tri_nho_plugin = du_lieu_plugin_can_dao()
    return _tri_nho_plugin

def _get_data_gg():
    global _du_lieu_gg
    if _du_lieu_gg is None:
        from du_phong.data_khung_gg import data_khung_gg
        _du_lieu_gg = data_khung_gg()
    return _du_lieu_gg

# ══════════════════════════════════════════════════════════════════ #
# MENU 1: DICH FILE                                                  #
# ══════════════════════════════════════════════════════════════════ #
def menu_dich_file():
    clr(); banner('Thiết Lập Dịch Thuật')

    LANG = {
        '1': ('auto', 'Tự động phát hiện'),
        '2': ('en', 'Tiếng Anh'),
        '3': ('ja', 'Tiếng Nhật'),
        '4': ('ko', 'Tiếng Hàn'),
        '5': ('zh-CN', 'Trung (Giản thể)'),
        '6': ('zh-TW', 'Trung (Phồn thể)'),
        '7': ('ru', 'Tiếng Nga'),
        '8': ('vi', 'Tiếng Việt'),
    }
    LANG_TO = {
        '1': ('vi', 'Tiếng Việt'),
        '2': ('en', 'Tiếng Anh'),
        '3': ('ja', 'Tiếng Nhật'),
        '4': ('zh-CN', 'Trung Giản thể'),
    }

    # --- Nhap duong dan ---
    duong_dan_str = nhap("Đường dẫn file lẻ / folder / file .zip")
    if not duong_dan_str:
        warn("Đã hủy"); return
    
    # Hieu ung animation kiem tra duong dan
    with console.status("[dim]Đang quét file...[/]", spinner="dots"):
        time.sleep(0.5)
        duong_dan = Path(duong_dan_str)
        if not duong_dan.exists():
            err(f"Không tìm thấy: {duong_dan}")
            input("\n  Nhấn Enter..."); return

    # --- Chon ngon ngu nguon ---
    console.print("\n  [dim]──────────────────────────────────────[/]")
    console.print("  [bold white]Ngôn Ngữ Nguồn[/]")
    tb_from = Table(box=None, show_header=False, padding=(0, 2))
    for k, (_, ten) in LANG.items():
        tb_from.add_row(f"[bold #00ffff]{k:>2}[/]", f"[white]{ten}[/]")
    console.print(tb_from)
    lf_key = input("  \033[95m❯ \033[0m").strip() or "1"
    lang_from = LANG.get(lf_key, LANG['1'])[0]

    # --- Chon ngon ngu dich ---
    console.print("\n  [dim]──────────────────────────────────────[/]")
    console.print("  [bold white]Ngôn Ngữ Đích[/]")
    tb_to = Table(box=None, show_header=False, padding=(0, 2))
    for k, (_, ten) in LANG_TO.items():
        tb_to.add_row(f"[bold #ff00ff]{k:>2}[/]", f"[white]{ten}[/]")
    console.print(tb_to)
    lt_key = input("  \033[95m❯ \033[0m").strip() or "1"
    lang_to = LANG_TO.get(lt_key, LANG_TO['1'])[0]

    # --- Chon thu muc dau ra ---
    console.print("\n  [dim]──────────────────────────────────────[/]")
    out_mac_dinh = str(duong_dan.parent / 'translated')
    out_dir_str = nhap(f"Lưu kết quả tại", out_mac_dinh)
    out_dir = Path(out_dir_str)

    # --- Chon plugin filter (neu co) ---
    pd = _get_plugin_data()
    plugins = pd.tat_ca_plugin_can_dao()
    ds_plugin_chon: list[str] = []
    if plugins and duong_dan.suffix.lower() == '.zip':
        console.print("\n")
        lua_chon = menu("BỘ LỌC PLUGIN (ZIP)", [
            ('1', 'Dịch TOÀN BỘ file trong zip'),
            ('2', f'Dịch theo Database ([bold #00ffff]{len(plugins)} plugin[/])'),
            ('3', 'Nhập thủ công'),
        ])
        if lua_chon == '2':
            ds_plugin_chon = plugins
            info(f"Đã nạp bộ lọc Database.")
        elif lua_chon == '3':
            nhap_plugin = nhap("Tên plugin (cách nhau dấu phẩy)")
            ds_plugin_chon = [x.strip() for x in nhap_plugin.split(',') if x.strip()]

    # --- Xac nhan ---
    clr(); banner('Xác Nhận Tiến Trình')
    tb_xn = Table(box=box.SIMPLE, show_header=False, padding=(0, 2), border_style="dim")
    tb_xn.add_row("[dim]Target[/]", f"[bold cyan]{duong_dan.name}[/]")
    tb_xn.add_row("[dim]Task[/]", f"[white]{lang_from}[/] [magenta]➔[/] [bold white]{lang_to}[/]")
    tb_xn.add_row("[dim]Output[/]", f"[cyan]{out_dir}[/]")
    if ds_plugin_chon:
        tb_xn.add_row("[dim]Filter[/]", f"[magenta]{len(ds_plugin_chon)} plugins[/]")
    console.print(Align.center(tb_xn))
    console.print()
    
    xn = nhap("Bắt đầu chạy AI? [y/N]", "y").lower()
    if xn not in ('y', 'yes', 'co', 'có'):
        warn("Đã hủy"); input("\n  Nhấn Enter..."); return

    # --- Chay dich ---
    asyncio.run(_chay_dich(duong_dan, out_dir, lang_from, lang_to, ds_plugin_chon))
    console.print()
    nhap("Nhấn Enter để quay lại")

async def _chay_dich(duong_dan: Path, out_dir: Path, lang_from: str, lang_to: str, ds_plugin: list[str]):
    from xu_ly_file.quet_sau import quet_sau
    from xu_ly_file.phan_loai_file import phan_loai_file
    from xu_ly_file.trich_noi_dung import trich_noi_dung
    from xu_ly_file.lap_lai_file import lap_lai_file
    from hau_kiem.kiem_tra_ban_dich import kiem_tra_ban_dich
    from cau_hinh.hang_so import thu_muc_ket_qua
    from xu_ly_file.tai_len_gofile import tai_len_gofile
    import zipfile

    from dieu_phoi.ghi_log import bat_console_trace

    TRACE_LIVE_ALL = True

    def _emit_trace_console(msg: str):
        console.print(msg, soft_wrap=True)

    def _in_tieu_de_file(ten_file_hien_thi: str, chi_so: int, tong: int):
        console.print(f"\n[bold #00ffff]── File {chi_so}/{tong}[/] [white]{ten_file_hien_thi}[/]")

    bat_console_trace(_emit_trace_console, enabled=True)

    router = _get_router()
    qs = quet_sau()
    pl = phan_loai_file()
    tr = trich_noi_dung()
    vd = kiem_tra_ban_dich()
    out_dir.mkdir(parents=True, exist_ok=True)

    def _tach_ban_an_toan(ban_dich, report):
        if isinstance(report, dict):
            return report.get('ban_xuat_de_xuat', ban_dich)
        return ban_dich

    def _tao_duong_dan_debug(goc: Path, nhan: str) -> Path:
        return goc.with_name(f"{goc.name}.{nhan}")

    def _ghi_hien_truong(goc_out: Path, noi_dung_goc: str, ban_dich_raw: str, ban_an_toan: str, report: dict | None, kt_raw: dict, kt_safe: dict):
        debug_dir = goc_out.parent / '__debug__'
        debug_dir.mkdir(parents=True, exist_ok=True)
        rel = goc_out.name
        base = debug_dir / rel
        p_orig = _tao_duong_dan_debug(base, 'orig')
        p_raw = _tao_duong_dan_debug(base, 'raw_out')
        p_safe = _tao_duong_dan_debug(base, 'safe_out')
        p_report = _tao_duong_dan_debug(base, 'report.json')
        p_orig.write_text(noi_dung_goc, encoding='utf-8')
        p_raw.write_text(ban_dich_raw, encoding='utf-8')
        p_safe.write_text(ban_an_toan, encoding='utf-8')
        report_out = {
            'trace_id': report.get('trace_id') if isinstance(report, dict) else None,
            'trace_file': report.get('trace_file') if isinstance(report, dict) else None,
            'nguon': report.get('nguon') if isinstance(report, dict) else None,
            'ly_do_xuat_de_xuat': report.get('nguon') if isinstance(report, dict) else None,
            'ban_xuat_de_xuat_la_goc': bool(report.get('can_xuat_goc')) if isinstance(report, dict) else False,
            'hau_kiem_raw': kt_raw,
            'hau_kiem_safe': kt_safe,
        }
        p_report.write_text(json.dumps(report_out, ensure_ascii=False, indent=2), encoding='utf-8')
        return {
            'orig': p_orig,
            'raw': p_raw,
            'safe': p_safe,
            'report': p_report,
        }

    def _chon_printer(out_obj):
        printer = getattr(out_obj, 'print', None)
        if callable(printer):
            return printer
        console_obj = getattr(out_obj, 'console', None)
        printer = getattr(console_obj, 'print', None)
        if callable(printer):
            return printer
        return None

    def _in_hau_kiem(out_obj, ten_file_hien_thi: str, noi_dung_goc: str, ban_dich_raw: str, ban_xuat: str):
        kiem_tra_raw = vd.kiem_tra(noi_dung_goc, ban_dich_raw)
        kiem_tra_xuat = vd.kiem_tra(noi_dung_goc, ban_xuat)

        loi_raw = sorted(set(kiem_tra_raw.get('loi', [])))
        loi_xuat = sorted(set(kiem_tra_xuat.get('loi', [])))
        printer = _chon_printer(out_obj)

        if printer and loi_raw:
            printer(f"  [bold yellow]⚠[/] RAW fail: [dim]{ten_file_hien_thi}[/] -> {', '.join(loi_raw)}")
        if printer and loi_xuat:
            printer(f"  [bold red]✖[/] XUẤT fail: [dim]{ten_file_hien_thi}[/] -> {', '.join(loi_xuat)}")

        return kiem_tra_raw, kiem_tra_xuat

    async def _dich_3_vong(noi_dung: str, ten_file: str, loai: str):
        last_ban, last_report = noi_dung, {'hau_kiem': {'hop_le': True, 'loi': []}}
        lich_su = []
        for mode in AUTO_MODES:
            ban_dich, report = await router.dich(noi_dung, ten_file, lang_from, lang_to, loai, mode=mode)
            report = report or {}
            report['mode'] = mode
            lich_su.append({'mode': mode, 'fail_count': _dem_fail_report(report), 'hop_le': bool((report.get('hau_kiem') or {}).get('hop_le'))})
            last_ban, last_report = ban_dich, report
            if (report.get('hau_kiem') or {}).get('hop_le'):
                report['lich_su_pass'] = lich_su
                return ban_dich, report, False
        last_report['lich_su_pass'] = lich_su
        return last_ban, last_report, _can_hardcore_report(last_report)

    def _hardcore_path_hop_le(seg):
        key = (getattr(seg, 'key', '') or '').strip().lower()
        path = (getattr(seg, 'path', '') or '').strip().lower()
        if not key:
            return False
        if key in {'menu_title', 'display_name', 'lore'}:
            return True
        if key.endswith('_commands') or key == 'deny_commands':
            return True
        if '.lore[' in path or '.display_name' in path or '.menu_title' in path:
            return True
        if any(x in path for x in ['.click_commands[', '.left_click_commands[', '.right_click_commands[', '.deny_commands[']):
            return True
        return False

    def _hardcore_text_hop_le(seg):
        import re
        txt = (getattr(seg, 'text', '') or '').strip()
        if not txt:
            return False
        if len(txt) > 180 and 'basehead-' in txt.lower():
            return False
        if re.fullmatch(r'[-=~_*+|.]{3,}', txt):
            return True
        if not re.search(r'[A-Za-zÀ-ỹ]', txt):
            return False
        if re.fullmatch(r'(?:[&§][0-9A-FK-ORa-fk-or]|&#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{6}|\s|[-=~_*+|])+', txt):
            return False
        low = txt.lower().strip()
        if low in {'has money', 'has permission', 'string equals ignorecase'}:
            return False
        if re.fullmatch(r'[a-z0-9_.:-]+', low) and (' ' not in low):
            if '.' in low or '_' in low:
                return False
        path = (getattr(seg, 'path', '') or '').lower()
        if any(x in path for x in ['.permission', '.material', '.slot', '.priority', '.amount', '.input', '.output', '.type']):
            return False
        if any(x in path for x in ['open_command', '.requirements', '.view_requirement']):
            return False
        if any(x in path for x in ['.click_commands[', '.left_click_commands[', '.right_click_commands[', '.deny_commands[']):
            cmd = low.lstrip()
            prefixes = (
                'eco take ', 'lp user ', 'permission set ', 'rawmsg ', 'tm msg ', 'ajparkour start ',
                'warp ', 'ca<', 'shop<', 'stats', 'quests', 'tags', 'perkshop', 'backpackshop', 'flightshop',
                'tfly give ', 'rs give spawner ', 'workbench', 'cartographytable', 'grindstone', 'loom',
                'smithingtable', 'stonecutter', 'rtp player ', 'casino', 'main_menu', 'spawner', 'spawnershop'
            )
            if cmd.startswith(prefixes):
                return False
            if '%player_name%' in cmd and not re.search(r'[A-Za-zÀ-ỹ]{3,}.*\s[A-Za-zÀ-ỹ]{3,}', cmd):
                return False
        return True

    def _normalize_hardcore_text(txt: str):
        import re
        s = (txt or '').strip()
        if not s:
            return ''
        if re.fullmatch(r'[-=~_*+|.]{3,}', s):
            return '<SEP>'
        s = re.sub(r'[-=~_*+|.]{3,}', '<SEP>', s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    def _lay_tat_ca_string_hardcore(noi_dung: str):
        segs = router.gg._phan_tich_segments(noi_dung.splitlines(keepends=True))
        ds = []
        seen = {}
        for seg in segs:
            txt = (seg.text or '').strip()
            if not txt:
                continue
            if seg.action not in {'dich_gg', 'cho_data'}:
                continue
            if not _hardcore_path_hop_le(seg):
                continue
            if not _hardcore_text_hop_le(seg):
                continue
            norm = _normalize_hardcore_text(txt)
            kind = 'sep' if norm == '<SEP>' else 'text'
            key = (kind, norm)
            info = seen.get(key)
            if info is None:
                info = {
                    'id': len(ds) + 1,
                    'text': seg.text,
                    'norm': norm,
                    'path': seg.path,
                    'seg': seg,
                    'count': 1,
                    'paths': [seg.path] if seg.path else [],
                    'samples': [seg.text],
                    'kind': kind,
                }
                seen[key] = info
                ds.append(info)
            else:
                info['count'] += 1
                if seg.path and seg.path not in info['paths']:
                    info['paths'].append(seg.path)
                if seg.text and seg.text not in info['samples'] and len(info['samples']) < 3:
                    info['samples'].append(seg.text)
        return ds

    def _tokenize_hardcore_text(text: str):
        import re
        text = text or ''
        pat = re.compile(
            r"((?:[&§][0-9A-FK-ORa-fk-or])+[-=~_*+|]{3,}|[-=~_*+|]{3,}|&#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{6}|(?:[&§][0-9A-FK-ORa-fk-or])+|%[^%\s]+%|<[^<>\n]+>|\d+(?:[.,]\d+)*|[A-Za-zÀ-ỹ]+(?:'[A-Za-zÀ-ỹ]+)?|[^\s])",
            re.UNICODE,
        )
        out = []
        for m in pat.finditer(text):
            tok = m.group(0)
            if tok and not tok.isspace():
                out.append(tok)
        return out or [text]

    def _parse_hardcore_header(line: str):
        skip_ids, fail_ids = set(), set()
        if not line.strip():
            return {'pass_all': True, 'block_all': False, 'skip_ids': skip_ids, 'fail_ids': fail_ids}
        if line.strip() == '0':
            return {'pass_all': False, 'block_all': True, 'skip_ids': skip_ids, 'fail_ids': fail_ids}
        for tok in line.split():
            if tok.endswith('F') and tok[:-1].isdigit():
                fail_ids.add(int(tok[:-1]))
            elif tok.isdigit():
                skip_ids.add(int(tok))
        return {'pass_all': False, 'block_all': False, 'skip_ids': skip_ids, 'fail_ids': fail_ids}

    async def _hardcore_batch(pending_items: list[dict]):
        if not pending_items:
            return
        console.print(f"\n[bold yellow]⚠[/] Bật HARDCORE cho [bold]{len(pending_items)}[/] file fail dai.")
        for item in pending_items:
            ds = _lay_tat_ca_string_hardcore(item['noi_dung'])
            if not ds:
                continue
            console.print(f"\n[bold yellow]HARDCORE[/] [white]{item['ten_file']}[/] [dim]({len(ds)} string cần check)[/]")
            da_doi = False
            for x in ds:
                hien_path = x.get('path') or ''
                if x.get('count', 1) > 1:
                    hien_path = f"{hien_path} [dim](trùng {x['count']} lần)[/]"
                console.print(f"\n  [bold yellow]STRING[/] [white]{x['id']}[/]")
                if hien_path:
                    console.print(f"  [dim]{hien_path}[/]", soft_wrap=True)
                console.print(f"  [white]{x['text']}[/]", soft_wrap=True)
                toks = _tokenize_hardcore_text(x['text'])
                if len(toks) <= 1 and toks[0] == x['text']:
                    console.print("    [dim]Không tách thêm được, giữ nguyên string để check.[/]")
                else:
                    for i, tok in enumerate(toks, 1):
                        console.print(f"    [bold #ff00ff]{i}.[/] {tok}", soft_wrap=True)
                line1 = nhap("Nhập: idF để tách lại, id để bỏ qua, 0 để chặn string này (Enter = cho qua)")
                parsed = _parse_hardcore_header(line1)
                if parsed['pass_all']:
                    continue
                if parsed['block_all']:
                    router.gg.manual_rules.set_skip(item['ten_file'], x['text'])
                    da_doi = True
                    continue
                locks = []
                for sid in sorted(parsed['skip_ids']):
                    if 1 <= sid <= len(toks):
                        tok = toks[sid - 1]
                        if tok not in locks:
                            locks.append(tok)
                if locks:
                    cur = router.gg.manual_rules.get(item['ten_file'], x['text']) or {}
                    merged = list(cur.get('locks', []) or [])
                    for z in locks:
                        if z not in merged:
                            merged.append(z)
                    router.gg.manual_rules.set_locks(item['ten_file'], x['text'], merged)
                    da_doi = True
                for sid in sorted(parsed['fail_ids']):
                    if 1 <= sid <= len(toks):
                        line2 = nhap(f"{sid}:")
                        more_locks = [z for z in line2.split() if z]
                        if more_locks:
                            cur = router.gg.manual_rules.get(item['ten_file'], x['text']) or {}
                            merged = list(cur.get('locks', []) or [])
                            for z in more_locks:
                                if z not in merged:
                                    merged.append(z)
                            router.gg.manual_rules.set_locks(item['ten_file'], x['text'], merged)
                            da_doi = True
            if da_doi:
                ban_dich, report = await router.dich(item['noi_dung'], item['ten_file'], lang_from, lang_to, item['loai'], mode='hardcore')
                item['ban_dich'] = ban_dich
                item['report'] = report or {}
                item['report']['mode'] = 'hardcore'

    scan = qs.quet(duong_dan, ds_plugin_can_dao=ds_plugin if ds_plugin else None)
    ds = scan.get('can_dich', [])
    
    if not ds:
        warn("Không có dữ liệu phù hợp để chạy.")
        return
        
    console.print(f"\n  [dim]Phát hiện [bold white]{len(ds)}[/] file hợp lệ...[/]\n")

    thanh_cong = 0; loi = 0; t0 = time.time()
    file_tai_len = None
    pending_hardcore = []

    # Khi bật trace live toàn phần thì ưu tiên log hiện vật, không giữ progress bar live để tránh bị nuốt màn hình.
    progress = None if TRACE_LIVE_ALL else Progress(
        TextColumn("  [bold #00ffff]{task.description}"),
        BarColumn(bar_width=None, style="grey23", complete_style="#ff00ff", finished_style="#00ffff"),
        TextColumn("[bold white]{task.percentage:>3.0f}%[/]"),
        console=console,
        expand=True
    )

    if scan.get('archive'):
        out_files = []
        tong = len(ds)
        if TRACE_LIVE_ALL:
            for i, ten_file in enumerate(ds, 1):
                _in_tieu_de_file(ten_file, i, tong)
                try:
                    noi_dung = tr.doc_trong_zip(duong_dan, ten_file)
                    loai = pl.lay_loai(ten_file) or 'text'
                    ban_dich, report, can_hc = await _dich_3_vong(noi_dung, ten_file, loai)
                    ban_an_toan = _tach_ban_an_toan(ban_dich, report)
                    if can_hc:
                        pending_hardcore.append({'ten_file': duong_dan.name, 'noi_dung': noi_dung, 'loai': loai, 'ban_dich': ban_dich, 'report': report})

                    out_path = thu_muc_ket_qua / 'cli_zip' / ten_file
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(ban_an_toan, encoding='utf-8')
                    kt_raw, kt_safe = _in_hau_kiem(console, ten_file, noi_dung, ban_dich, ban_an_toan)
                    debug_paths = _ghi_hien_truong(out_path, noi_dung, ban_dich, ban_an_toan, report or {}, kt_raw, kt_safe)

                    out_files.append((out_path, ten_file))
                    out_files.append((debug_paths['orig'], f'__debug__/{ten_file}.orig'))
                    out_files.append((debug_paths['raw'], f'__debug__/{ten_file}.raw_out'))
                    out_files.append((debug_paths['safe'], f'__debug__/{ten_file}.safe_out'))
                    out_files.append((debug_paths['report'], f'__debug__/{ten_file}.report.json'))
                    thanh_cong += 1
                except Exception as e:
                    console.print(f"  [bold red]✖[/] Lỗi dịch: [dim]{ten_file}[/] - {e}")
                    loi += 1
        else:
            with progress:
                task_id = progress.add_task("Chuẩn bị...", total=len(ds))
                for i, ten_file in enumerate(ds, 1):
                    hien_thi = ten_file if len(ten_file) < 25 else "..." + ten_file[-22:]
                    progress.update(task_id, description=f"{hien_thi:<25}")
                    try:
                        noi_dung = tr.doc_trong_zip(duong_dan, ten_file)
                        loai = pl.lay_loai(ten_file) or 'text'
                        ban_dich, report, can_hc = await _dich_3_vong(noi_dung, ten_file, loai)
                        ban_an_toan = _tach_ban_an_toan(ban_dich, report)
                        if can_hc:
                            pending_hardcore.append({'ten_file': ten_file, 'noi_dung': noi_dung, 'loai': loai, 'ban_dich': ban_dich, 'report': report})

                        out_path = thu_muc_ket_qua / 'cli_zip' / ten_file
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        out_path.write_text(ban_an_toan, encoding='utf-8')
                        kt_raw, kt_safe = _in_hau_kiem(progress, ten_file, noi_dung, ban_dich, ban_an_toan)
                        debug_paths = _ghi_hien_truong(out_path, noi_dung, ban_dich, ban_an_toan, report or {}, kt_raw, kt_safe)

                        out_files.append((out_path, ten_file))
                        out_files.append((debug_paths['orig'], f'__debug__/{ten_file}.orig'))
                        out_files.append((debug_paths['raw'], f'__debug__/{ten_file}.raw_out'))
                        out_files.append((debug_paths['safe'], f'__debug__/{ten_file}.safe_out'))
                        out_files.append((debug_paths['report'], f'__debug__/{ten_file}.report.json'))
                        thanh_cong += 1
                    except Exception as e:
                        progress.console.print(f"  [bold red]✖[/] Lỗi dịch: [dim]{ten_file}[/] - {e}")
                        loi += 1
                    progress.advance(task_id, 1)

        ten_zip = out_dir / f"{duong_dan.stem}_translated.zip"
        with console.status("[dim]Đang đóng gói ZIP...[/]", spinner="bouncingBar"):
            with zipfile.ZipFile(ten_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                for out_path, arc_name in out_files:
                    zf.write(out_path, arcname=arc_name)
        file_tai_len = ten_zip
        console.print()
        ok(f"Đã lưu: [cyan]{ten_zip.name}[/]")

    elif duong_dan.is_dir():
        out_files = []
        tong = len(ds)
        if TRACE_LIVE_ALL:
            for i, rel in enumerate(ds, 1):
                hien_thi = str(rel)
                _in_tieu_de_file(hien_thi, i, tong)
                src = duong_dan / rel
                try:
                    noi_dung = tr.doc_file(src)
                    loai = pl.lay_loai(src.name) or 'text'
                    ban_dich, report, can_hc = await _dich_3_vong(noi_dung, src.name, loai)
                    ban_an_toan = _tach_ban_an_toan(ban_dich, report)
                    if can_hc:
                        pending_hardcore.append({'ten_file': duong_dan.name, 'noi_dung': noi_dung, 'loai': loai, 'ban_dich': ban_dich, 'report': report})
                    out_path = out_dir / rel
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(ban_an_toan, encoding='utf-8')
                    kt_raw, kt_safe = _in_hau_kiem(console, str(rel), noi_dung, ban_dich, ban_an_toan)
                    _ghi_hien_truong(out_path, noi_dung, ban_dich, ban_an_toan, report or {}, kt_raw, kt_safe)
                    out_files.append((out_path, rel))
                    thanh_cong += 1
                except Exception as e:
                    console.print(f"  [bold red]✖[/] Lỗi: [dim]{rel}[/] - {e}")
                    loi += 1
        else:
            with progress:
                task_id = progress.add_task("Đang dịch...", total=len(ds))
                for i, rel in enumerate(ds, 1):
                    hien_thi = str(rel) if len(str(rel)) < 25 else "..." + str(rel)[-22:]
                    progress.update(task_id, description=f"{hien_thi:<25}")
                    src = duong_dan / rel
                    try:
                        noi_dung = tr.doc_file(src)
                        loai = pl.lay_loai(src.name) or 'text'
                        ban_dich, report, can_hc = await _dich_3_vong(noi_dung, src.name, loai)
                        ban_an_toan = _tach_ban_an_toan(ban_dich, report)
                        if can_hc:
                            pending_hardcore.append({'ten_file': src.name, 'noi_dung': noi_dung, 'loai': loai, 'ban_dich': ban_dich, 'report': report})
                        out_path = out_dir / rel
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        out_path.write_text(ban_an_toan, encoding='utf-8')
                        kt_raw, kt_safe = _in_hau_kiem(progress, str(rel), noi_dung, ban_dich, ban_an_toan)
                        _ghi_hien_truong(out_path, noi_dung, ban_dich, ban_an_toan, report or {}, kt_raw, kt_safe)
                        out_files.append((out_path, rel))
                        thanh_cong += 1
                    except Exception as e:
                        progress.console.print(f"  [bold red]✖[/] Lỗi: [dim]{rel}[/] - {e}")
                        loi += 1
                    progress.advance(task_id, 1)

        if out_files:
            ten_zip = out_dir / f"{duong_dan.name}_translated.zip"
            with console.status("[dim]Đang đóng gói ZIP...[/]", spinner="bouncingBar"):
                with zipfile.ZipFile(ten_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for out_path, arc_name in out_files:
                        zf.write(out_path, arcname=str(arc_name).replace(chr(92), '/'))
            file_tai_len = ten_zip
            console.print()
            ok(f"Đã lưu: [cyan]{ten_zip.name}[/]")
    else:
        if TRACE_LIVE_ALL:
            _in_tieu_de_file(duong_dan.name, 1, 1)
            try:
                noi_dung = tr.doc_file(duong_dan)
                loai = pl.lay_loai(duong_dan.name) or 'text'
                ban_dich, report, can_hc = await _dich_3_vong(noi_dung, duong_dan.name, loai)
                ban_an_toan = _tach_ban_an_toan(ban_dich, report)
                if can_hc:
                    pending_hardcore.append({'ten_file': duong_dan.name, 'noi_dung': noi_dung, 'loai': loai, 'ban_dich': ban_dich, 'report': report})
                ten_out = f"{duong_dan.stem}_translated{duong_dan.suffix}"
                file_tai_len = out_dir / ten_out
                file_tai_len.write_text(ban_an_toan, encoding='utf-8')
                kt_raw, kt_safe = _in_hau_kiem(console, duong_dan.name, noi_dung, ban_dich, ban_an_toan)
                _ghi_hien_truong(file_tai_len, noi_dung, ban_dich, ban_an_toan, report or {}, kt_raw, kt_safe)
                thanh_cong += 1
            except Exception as e:
                console.print(f"  [bold red]✖[/] Lỗi: {e}")
                loi += 1
        else:
            with progress:
                task_id = progress.add_task("Đang dịch...", total=1)
                try:
                    noi_dung = tr.doc_file(duong_dan)
                    loai = pl.lay_loai(duong_dan.name) or 'text'
                    ban_dich, report, can_hc = await _dich_3_vong(noi_dung, duong_dan.name, loai)
                    ban_an_toan = _tach_ban_an_toan(ban_dich, report)
                    if can_hc:
                        pending_hardcore.append({'ten_file': duong_dan.name, 'noi_dung': noi_dung, 'loai': loai, 'ban_dich': ban_dich, 'report': report})
                    ten_out = f"{duong_dan.stem}_translated{duong_dan.suffix}"
                    file_tai_len = out_dir / ten_out
                    file_tai_len.write_text(ban_an_toan, encoding='utf-8')
                    kt_raw, kt_safe = _in_hau_kiem(progress, duong_dan.name, noi_dung, ban_dich, ban_an_toan)
                    _ghi_hien_truong(file_tai_len, noi_dung, ban_dich, ban_an_toan, report or {}, kt_raw, kt_safe)
                    thanh_cong += 1
                except Exception as e:
                    progress.console.print(f"  [bold red]✖[/] Lỗi: {e}")
                    loi += 1
                progress.advance(task_id, 1)

        if thanh_cong > 0:
            console.print()
            ok(f"Đã lưu: [cyan]{file_tai_len.name}[/]")
    if pending_hardcore:
        await _hardcore_batch(pending_hardcore)

    from dieu_phoi.ghi_log import tat_console_trace
    tat_console_trace()

    elapsed = time.time() - t0
    console.print("  [dim]──────────────────────────────────────[/]")
    ok(f"Hoàn thành: [bold green]{thanh_cong}/{len(ds)}[/] files ([dim]{elapsed:.1f}s[/])")
    if loi: warn(f"Thất bại: [bold red]{loi}[/] files")

    if file_tai_len and file_tai_len.exists():
        try:
            with console.status("[dim]Đang tải lên Cloud (Gofile)...[/]", spinner="line"):
                uploader = tai_len_gofile()
                ket_qua_tai = await uploader.tai_len(file_tai_len)

            if ket_qua_tai.get('link'):
                ok(f"Link tải: [bold underline #00ffff]{ket_qua_tai['link']}[/]")
            else:
                warn('Upload Cloud thất bại.')
        except Exception as e:
            warn(f"Lỗi Cloud: {e}")
# ══════════════════════════════════════════════════════════════════ #
# MENU 2: QUET PLUGIN                                                #
# ══════════════════════════════════════════════════════════════════ #
def menu_quet_plugin():
    clr(); banner('Scanner')

    duong_dan_str = nhap("Nhập file zip / folder plugins", "./plugins")
    if not duong_dan_str:
        warn("Hủy"); return
    duong_dan = Path(duong_dan_str)
    if not duong_dan.exists():
        err(f"Không tìm thấy dữ liệu.")
        nhap("Nhấn Enter để quay lại"); return

    from xu_ly_file.quet_folder_ngoai import quet_folder_ngoai
    
    with console.status("[dim]Đang phân tích cấu trúc...[/]", spinner="dots"):
        qn = quet_folder_ngoai()
        ket_qua = qn.quet(duong_dan)
        muc = ket_qua.get('muc', [])

    if not muc:
        warn("Không phát hiện folder plugin.")
        nhap("Nhấn Enter để quay lại"); return

    console.print(f"\n  [bold white]KẾT QUẢ SCAN ([cyan]{len(muc)}[/] objects)[/]")
    console.print("  [dim]──────────────────────────────────────[/]")
    
    tb = Table(box=None, show_header=False, padding=(0, 2))
    
    BADGE = {
        'nen_dao': "[green]NÊN ĐÀO[/]",
        'can_than': "[yellow]WARNING[/]",
        'bo_qua':  "[dim]BỎ QUA[/]",
        'xem_them':"[cyan]CHECK[/]",
    }
    
    for item in muc:
        badge = BADGE.get(item['goi_y'], item['goi_y'])
        tb.add_row(
            f"[bold #ff00ff]{item['id']:>2}[/]", 
            f"[white]{item['ten'][:20]}[/]", 
            badge, 
            f"[dim]{item['so_file_hop_le']}/{item['tong_file']}[/]"
        )
    console.print(tb)
    console.print("  [dim]──────────────────────────────────────[/]\n")

    hanh_dong = menu("LỰA CHỌN", [
        ('1', 'Lưu plugin theo ID'),
        ('2', 'Lưu Auto (Tất cả NÊN ĐÀO)'),
        ('3', 'Chi tiết ID'),
        ('0', 'Quay lại'),
    ])

    pd = _get_plugin_data()
    if hanh_dong == '1':
        so_list = nhap("Nhập ID (VD: 1,3,5 hoặc 1-5)")
        chon_ids = _parse_so_list(so_list, len(muc))
        da_chon = [muc[i-1] for i in chon_ids if 1 <= i <= len(muc)]
        for item in da_chon:
            pd.them_plugin(item['ten'])
            ok(f"Saved: [cyan]{item['ten']}[/]")
        if da_chon:
            ok(f"Total saved: {len(pd.tat_ca_plugin_can_dao())}")

    elif hanh_dong == '2':
        ds_nen = [x for x in muc if x['goi_y'] == 'nen_dao']
        for item in ds_nen:
            pd.them_plugin(item['ten'])
        ok(f"Saved {len(ds_nen)} objects.")

    elif hanh_dong == '3':
        so = nhap("Nhập ID")
        if so.isdigit():
            idx = int(so) - 1
            if 0 <= idx < len(muc):
                item = muc[idx]
                console.print(f"\n  [bold cyan]Object:[/] [white]{item['ten']}[/]")
                console.print(f"  [dim]Path  :[/] {item['path']}")
                console.print(f"  [dim]Files :[/] {item['so_file_hop_le']}/{item['tong_file']}")
                console.print(f"  [dim]Tag   :[/] {item['goi_y']}")

    nhap("Nhấn Enter để quay lại")

def _parse_so_list(s: str, max_n: int) -> list[int]:
    result = set()
    for part in s.split(','):
        part = part.strip()
        if '-' in part:
            a, _, b = part.partition('-')
            if a.isdigit() and b.isdigit():
                result.update(range(int(a), int(b)+1))
        elif part.isdigit():
            result.add(int(part))
    return sorted(x for x in result if 1 <= x <= max_n)

# ══════════════════════════════════════════════════════════════════ #
# MENU 3: QUAN LY PLUGIN                                             #
# ══════════════════════════════════════════════════════════════════ #
def menu_quan_ly_plugin():
    while True:
        clr(); banner('Database Plugin')
        pd = _get_plugin_data()
        ds = pd.tat_ca_plugin_can_dao()
        ds_bo_qua = pd.plugin_bo_qua()

        console.print(f"  [bold white]Target List ([cyan]{len(ds)}[/])[/]")
        if ds:
            tb = Table(box=None, show_header=False, padding=(0, 2))
            for i, p in enumerate(ds[:10], 1):
                tb.add_row(f"[bold #ff00ff]{i:>2}[/]", p)
            console.print(tb)
            if len(ds) > 10:
                console.print(f"  [dim]... và {len(ds)-10} plugin khác.[/]")
        else:
            warn("Database trống.")
            
        console.print(f"\n  [dim]Ignored: {', '.join(ds_bo_qua[:3])}...[/dim]\n")

        hanh_dong = menu("HÀNH ĐỘNG", [
            ('1', 'Thêm thủ công'),
            ('2', 'Xóa theo ID'),
            ('3', 'Clear toàn bộ thủ công'),
            ('4', 'Xem Full List'),
            ('0', 'Quay lại'),
        ])

        if hanh_dong == '0': break
        elif hanh_dong == '1':
            ten = nhap("Tên plugin")
            if ten:
                pd.them_plugin(ten); ok(f"Added: [cyan]{ten}[/]")
        elif hanh_dong == '2':
            so = nhap("ID cần xóa")
            chon_ids = _parse_so_list(so, len(ds))
            for idx in sorted(chon_ids, reverse=True):
                ten = ds[idx-1]
                pd.xoa_plugin(ten); ok(f"Removed: [cyan]{ten}[/]")
        elif hanh_dong == '3':
            xn = nhap("Clear all user plugins? [y/N]", "n")
            if xn.lower() == 'y':
                pd.du_lieu['plugin_nguoi_dung'] = []
                pd.luu(); ok("Cleared.")
        elif hanh_dong == '4':
            console.print("\n  [bold white]FULL LIST[/]")
            for i, p in enumerate(ds, 1):
                console.print(f"  [dim]{i:>3}.[/] {p}")
            nhap("Nhấn Enter để quay lại")

# ══════════════════════════════════════════════════════════════════ #
# MENU 4: QUAN LY KEY                                                #
# ══════════════════════════════════════════════════════════════════ #
def menu_quan_ly_key():
    while True:
        clr(); banner('API Config')
        from cau_hinh.cai_dat import cai_dat_he_thong
        keys = cai_dat_he_thong().gemini_api_keys

        console.print(f"  [bold white]Active Keys ([cyan]{len(keys)}[/])[/]")
        if keys:
            tb = Table(box=None, show_header=False, padding=(0, 2))
            for i, k in enumerate(keys, 1):
                short = f"{k[:8]}****{k[-4:]}" if len(k) > 12 else k
                tb.add_row(f"[{i}]", f"[cyan]{short}[/]", "[green]✔ OK[/]")
            console.print(tb)
            console.print("\n")
        else:
            warn("Chưa có API Key. Tool không thể hoạt động.\n")

        hanh_dong = menu("HÀNH ĐỘNG", [
            ('1', 'Add Key mới'),
            ('2', 'Test Connection'),
            ('3', 'Get Free Key (Hướng dẫn)'),
            ('4', 'Remove Key'),
            ('0', 'Quay lại'),
        ])

        if hanh_dong == '0': break
        elif hanh_dong == '1':
            key = nhap("Dán API Key (AIza...)")
            if key:
                _them_key_vao_env(key)
                from cau_hinh.cai_dat import cai_dat_mac_dinh
                cai_dat_mac_dinh.gemini_api_keys.append(key)
                _get_router().gemini.them_key(key)
                ok(f"Added: [cyan]{key[:8]}...[/]")
        elif hanh_dong == '2':
            if not keys:
                warn("Chưa có key")
            else:
                with console.status("[dim]Pinging Gemini API...[/]", spinner="point"):
                    asyncio.run(_test_key())
                nhap("Nhấn Enter để tiếp tục")
        elif hanh_dong == '3':
            clr(); banner('Get API Key')
            console.print(f"""
  [white]1. Truy cập:[/white] [cyan underline]https://aistudio.google.com/app/apikey[/]
  [white]2. Tạo Key mới (Bắt đầu bằng AIza...)[/white]
  [white]3. Dán vào Menu 1.[/white]
  [dim]Mẹo: Thêm nhiều key để tự động xoay vòng request.[/dim]
""")
            nhap("Nhấn Enter để quay lại")
        elif hanh_dong == '4':
            if not keys:
                warn("Chưa có key")
            else:
                so = nhap("ID Key cần xóa")
                if so.isdigit() and 1 <= int(so) <= len(keys):
                    key_xoa = keys.pop(int(so)-1)
                    ok(f"Removed: [cyan]{key_xoa[:8]}...[/]")

def _them_key_vao_env(key: str):
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        noi_dung = env_file.read_text(encoding='utf-8')
        if 'GEMINI_API_KEYS=' in noi_dung:
            import re
            noi_dung = re.sub(r'(GEMINI_API_KEYS=.*)', r'\1,' + key, noi_dung)
        elif 'GEMINI_API_KEY=' not in noi_dung:
            noi_dung += f'\nGEMINI_API_KEY={key}\n'
        env_file.write_text(noi_dung, encoding='utf-8')
    else:
        env_file.write_text(f'GEMINI_API_KEY={key}\n', encoding='utf-8')

async def _test_key():
    from loi.gemini_loi import gemini_loi
    from cau_hinh.cai_dat import cai_dat_he_thong
    g = gemini_loi(cai_dat_he_thong())
    if not g.keys:
        err("Không có key"); return
    ket_qua, ok_flag = await g.translate_text("Hello World", "test.txt", "en", "vi")
    if ok_flag:
        ok(f"Connection OK. Ping: [cyan]{ket_qua[:30]}[/]")
    else:
        err("Connection Failed.")

# ══════════════════════════════════════════════════════════════════ #
# MENU 5: THONG KE & LOG                                             #
# ══════════════════════════════════════════════════════════════════ #
def menu_thong_ke():
    clr(); banner('System Info')
    from cau_hinh.cai_dat import cai_dat_mac_dinh
    from cau_hinh.hang_so import thu_muc_bao_cao, thu_muc_log, thu_muc_tri_nho

    c = cai_dat_mac_dinh
    console.print("  [bold white]Cấu Hình Boot[/]")
    tb = Table(box=None, show_header=False, padding=(0, 3))
    tb.add_row("[dim]Core[/]", f"[cyan]{c.bot_version}[/]")
    tb.add_row("[dim]Models[/]", f"[cyan]{', '.join(c.gemini_models)}[/]")
    tb.add_row("[dim]Keys[/]", f"[bold {'green' if c.gemini_api_keys else 'red'}]{len(c.gemini_api_keys)}[/]")
    tb.add_row("[dim]Cache[/]", f"[bold {'green' if c.enable_cache else 'dim'}]{'ON' if c.enable_cache else 'OFF'}[/]")
    console.print(tb)

    try:
        bc_files = list(thu_muc_bao_cao.glob('*.json'))
        console.print(f"\n  [dim]Total Jobs:[/] [bold green]{len(bc_files)}[/]\n")
    except Exception:
        pass

    hanh_dong = menu("HÀNH ĐỘNG", [
        ('1', 'View System Log'),
        ('2', 'Clear Log'),
        ('3', 'View Cache Memory'),
        ('0', 'Quay lại'),
    ])
    if hanh_dong == '1':
        _xem_log_day_du()
    elif hanh_dong == '2':
        xn = nhap("Clear system log? [y/N]", "n")
        if xn.lower() == 'y':
            (thu_muc_log / 'he_thong.log').write_text('', encoding='utf-8')
            ok("Log cleared.")
    elif hanh_dong == '3':
        _xem_cache()

def _xem_log_day_du():
    from cau_hinh.hang_so import thu_muc_log
    log_file = thu_muc_log / 'he_thong.log'
    if not log_file.exists() or not log_file.read_text(encoding='utf-8').strip():
        warn("Log is empty."); return
    lines = log_file.read_text(encoding='utf-8').splitlines()
    console.print(f"\n  [dim]Showing {len(lines)} lines...[/]")
    try:
        for line in lines[-30:]:
            color = "red" if 'ERROR' in line else ("yellow" if 'WARNING' in line else "dim")
            console.print(f"  [{color}]{line}[/]")
    except KeyboardInterrupt:
        pass
    nhap("Nhấn Enter để quay lại")

def _xem_cache():
    from cau_hinh.hang_so import thu_muc_tri_nho
    cache_file = thu_muc_tri_nho / 'bo_nho_dich.json'
    if not cache_file.exists():
        warn("Cache is empty."); return
    data = json.loads(cache_file.read_text(encoding='utf-8'))
    console.print(f"\n  [bold white]Cache Size:[/] [green]{len(data)}[/] items")
    for i, (k, v) in enumerate(list(data.items())[:5]):
        console.print(f"  [dim]{k[:16]}[/] → {v[:40]}...")
    nhap("Nhấn Enter để quay lại")

# ══════════════════════════════════════════════════════════════════ #
# CÁC MENU KHÁC (6, 7, 8, 9)                                         #
# ══════════════════════════════════════════════════════════════════ #
def menu_scan_file():
    clr(); banner('File Preview')
    duong_dan_str = nhap("Đường dẫn file")
    if not duong_dan_str:
        warn("Hủy"); return
    duong_dan = Path(duong_dan_str)
    if not duong_dan.exists():
        err("Không tìm thấy."); nhap("Enter..."); return

    from xu_ly_file.quet_sau import quet_sau
    
    with console.status("[dim]Đang quét file...[/]"):
        qs = quet_sau()
        kq = qs.quet(duong_dan)

    console.print(f"\n  [bold white]Report: {duong_dan.name}[/]")
    tb = Table(box=None, show_header=False, padding=(0, 2))
    tb.add_row("Tổng file", str(kq['tong']))
    tb.add_row("Hợp lệ", f"[bold green]{len(kq['can_dich'])}[/]")
    tb.add_row("Bỏ qua", f"[dim]{len(kq['bo_qua'])}[/]")
    console.print(tb)

    nhap("Nhấn Enter để quay lại")

def menu_du_lieu_gg():
    from cau_hinh.hang_so import thu_muc_du_lieu_gg
    while True:
        clr(); banner('GG Shield Engine')
        bo = _get_data_gg()
        thong_ke = bo.nap(force=False)

        tb = Table(box=None, show_header=False, padding=(0, 2))
        tb.add_row("[dim]Khung Dịch[/]", f"[bold cyan]{thong_ke['khung_dich']}[/]")
        tb.add_row("[dim]Khung Cấm[/]", f"[bold yellow]{thong_ke['khung_cam']}[/]")
        console.print(tb)
        console.print()

        hanh_dong = menu("HÀNH ĐỘNG", [
            ('1', 'Tạo Database Mẫu'),
            ('2', 'Reload Database'),
            ('0', 'Quay lại'),
        ])
        if hanh_dong == '0': break
        elif hanh_dong == '1':
            bo.tao_mau_neu_thieu()
            bo.nap(force=True)
            ok('Đã tạo.')
        elif hanh_dong == '2':
            bo.nap(force=True)
            ok(f"Reloaded.")

def menu_web_panel():
    clr(); banner('Web Engine')
    port = nhap("Port", "8000")
    host = nhap("Host", "0.0.0.0")
    console.print(f"""
  [bold green]●[/] Web UI : [cyan underline]http://127.0.0.1:{port}[/]
  [bold green]●[/] API    : [cyan underline]http://127.0.0.1:{port}/api/docs[/]
  [dim]Nhấn Ctrl+C để Stop[/dim]
""")
    try:
        import uvicorn
    except ImportError:
        err("Missing: pip install uvicorn fastapi")
        nhap("Nhấn Enter để quay lại")
        return
    try:
        uvicorn.run('giao_tiep.api_rest:app', host=host, port=int(port), reload=False)
    except KeyboardInterrupt:
        console.print(f"\n  [bold yellow]Server Stopped.[/]")
    except Exception as e:
        err(f"Lỗi web panel: {type(e).__name__}: {e}")
    nhap("Nhấn Enter để quay lại")

def menu_cai_dat_nhanh():
    clr(); banner('Môi Trường (.env)')
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        console.print(f"\n  [dim]{env_file.read_text(encoding='utf-8').strip()}[/]\n")
    else:
        warn("File .env chưa tồn tại.\n")

    hanh_dong = menu("HÀNH ĐỘNG", [
        ('1', 'Inject Key vào .env'),
        ('2', 'Tạo file .env gốc'),
        ('0', 'Quay lại'),
    ])
    if hanh_dong == '1':
        key = nhap("API Key")
        if key:
            _them_key_vao_env(key)
            ok("Injected.")
    elif hanh_dong == '2':
        content = "GEMINI_API_KEY=AIzaSy_YOUR_KEY_HERE\n"
        env_file.write_text(content, encoding='utf-8')
        ok("Created.")

# ══════════════════════════════════════════════════════════════════ #
# MENU CHINH                                                         #
# ══════════════════════════════════════════════════════════════════ #
def menu_chinh():
    boot_animation() # Animation chay 1 lan duy nhat luc khoi dong
    
    while True:
        nap_cfg_panel(force=True)
        clr(); banner()
        from cau_hinh.cai_dat import cai_dat_he_thong
        pd = _get_plugin_data()
        n_keys = len(cai_dat_he_thong().gemini_api_keys)
        n_plugin = len(pd.tat_ca_plugin_can_dao())

        key_status = f"[bold #00ffff]{n_keys}[/] keys" if n_keys else f"[bold red]No keys[/]"
        plugin_status = f"[bold #ff00ff]{n_plugin}[/] plugins"

        info_panel = Table.grid(padding=(0, 4))
        info_panel.add_row(f"[dim]API:[/] {key_status}", f"[dim]DB:[/] {plugin_status}")
        console.print(Align.center(info_panel))
        console.print()

        muc_menu_chinh = [
            ('1', 'Dịch Thuật (File / Folder / Zip)'),
            ('2', 'Scanner (Quét Plugin)'),
            ('3', 'Database Plugin'),
            ('4', 'Quản Lý API Keys'),
            ('5', 'Thống Kê Hệ Thống'),
            ('6', 'Khởi Chạy Web Panel (UI)'),
            ('0', 'Thoát Hệ Thống'),
        ]
        
        hanh_dong = menu("SYSTEM CORE", muc_menu_chinh)

        if hanh_dong == '0':
            clr()
            console.print(f"\n  [bold #00ffff]Hệ thống đã tắt. Hẹn gặp lại![/]\n")
            break
        elif hanh_dong == '1': menu_dich_file()
        elif hanh_dong == '2': menu_quet_plugin()
        elif hanh_dong == '3': menu_quan_ly_plugin()
        elif hanh_dong == '4': menu_quan_ly_key()
        elif hanh_dong == '5': menu_thong_ke()
        elif hanh_dong == '6': menu_web_panel()

if __name__ == '__main__':
    tao_cfg_panel_neu_thieu()
    nap_cfg_panel(force=True)
    menu_chinh()
