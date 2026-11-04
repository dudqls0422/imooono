"""구조계산서 첨부용 엑셀 양식(.xlsm) 생성 스크립트.

Excel COM(pywin32)으로 "설정" / "계산서" 두 시트짜리 통합 문서를 만들고,
머리글·바닥글 이미지와 머리글 자동 반영 매크로(vba/)를 넣어 .xlsm 으로 저장합니다.

사용법:
    python -m tools.calc_sheet_template                 # 기본 로고 경로 사용
    python -m tools.calc_sheet_template --logo 로고.png
    python -m tools.calc_sheet_template --out 다른위치.xlsm

로고는 매 실행마다 --logo 원본에서 assets/logo.png 로 다시 만듭니다(원본은 읽기만 함).
원본이 없으면 기존 assets/logo.png 를, 그것도 없으면 자리표시 이미지를 씁니다.
"""

from __future__ import annotations

import argparse
import ctypes
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
VBA_DIR = HERE / "vba"

DEFAULT_OUT = HERE / "구조계산서_양식.xlsm"

LOGO_NAME = "logo.png"
PLACEHOLDER_NAME = "logo_placeholder.png"
FOOTER_NAME = "footer.png"
HEADER_NAME = "header.png"

DOC_TITLE = "구조계산서(Structural Design and Analysis)"
TITLE_PT = 9.0
TITLE_GAP_MM = 2.0  # 머리글 이미지: 로고와 문서명 사이
PROJECT_GAP_MM = 3.0  # 프로젝트명 폭 계산: 머리글 이미지 오른쪽 끝 + 여유
PROJECT_SIZES = (9, 8, 7)  # 프로젝트명 글꼴 단계 (pt)
# 영문·숫자·공백 폭 측정용 견본 (프로젝트명에 흔한 문자 구성)
ASCII_SAMPLE = "Bldg 641-8 Seoul Office B1F/5F (Rev.2) No.12 abcdefgh 0123456789"

SETTINGS_SHEET = "설정"
CALC_SHEET = "계산서"
NOTES_FIRST_ROW = 7

COMPANY_MARK = "SNP"
COMPANY_TEXT = " STRUCTURAL ENGINEERING CO., LTD [ 건축구조기술사사무소 / 안전진단전문기관 ]"
FONT_BOLD = Path(r"C:\Windows\Fonts\malgunbd.ttf")

# 페이지 설정 (mm)
PAGE_MARGIN_LR = 15.0
PAGE_MARGIN_TOP = 21.0
PAGE_MARGIN_BOTTOM = 19.0
HEADER_MARGIN = 8.0
FOOTER_MARGIN = 7.0
PRINT_WIDTH_MM = 210.0 - 2 * PAGE_MARGIN_LR  # 180mm
N_COLS = 26  # A ~ Z
MARGIN_SLACK_MM = 0.25
HEADER_LOGO_MM = 10.0
FOOTER_LOGO_MM = 5.0

# 선 색 / 두께 (참고본 실측: 회색 약 35%, 1.98pt ≈ 0.7mm)
RULE_RGB = (89, 89, 89)
RULE_MM = 0.7

FOOTER_DPI = 300
ICO_FRAME_PX = 128

# Excel / VBE 상수
XL_WBA_WORKSHEET = -4167
XL_OPENXML_MACRO = 52
XL_PAPER_A4 = 9
XL_PORTRAIT = 1
XL_EDGE_BOTTOM = 9
XL_THICK = 4
XL_CONTINUOUS = 1
XL_AUTOMATIC = -4105
VBEXT_CT_DOCUMENT = 100


def mm_to_pt(mm: float) -> float:
    return mm * 72.0 / 25.4


def mm_to_px(mm: float, dpi: int = FOOTER_DPI) -> int:
    return round(mm / 25.4 * dpi)


def warn(msg: str) -> None:
    print(f"[경고] {msg}", file=sys.stderr)


def info(msg: str) -> None:
    print(f"[정보] {msg}")


# ---------------------------------------------------------------- 로고 / 이미지


def load_logo_image(src: Path) -> Image.Image:
    """원본 로고를 RGBA 이미지로 읽는다. .ico 는 128px 프레임(없으면 가장 큰 프레임)을 고른다.

    원본 파일은 읽기만 한다(메모리로 복사한 뒤 바로 닫음).
    """
    with Image.open(src) as img:
        if img.format == "ICO":
            sizes = sorted(img.info.get("sizes", {img.size}), key=lambda s: s[0] * s[1])
            want = (ICO_FRAME_PX, ICO_FRAME_PX)
            img.size = want if want in sizes else sizes[-1]
            img.load()
        return img.convert("RGBA").copy()


def make_placeholder(path: Path) -> Path:
    """회색 박스 + "LOGO" 글자의 128px 자리표시 이미지."""
    img = Image.new("RGBA", (ICO_FRAME_PX, ICO_FRAME_PX), (200, 200, 200, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, ICO_FRAME_PX - 1, ICO_FRAME_PX - 1], outline=(120, 120, 120, 255), width=4)
    font = ImageFont.truetype(str(FONT_BOLD), 34)
    d.text((ICO_FRAME_PX / 2, ICO_FRAME_PX / 2), "LOGO", fill=(90, 90, 90, 255), font=font, anchor="mm")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


def resolve_logo(src: Path | None, assets: Path = ASSETS) -> tuple[Path, str]:
    """사용할 로고 PNG 경로와 출처("source" / "cached" / "placeholder")를 돌려준다."""
    logo_png = assets / LOGO_NAME
    if src is not None and src.exists():
        img = load_logo_image(src)
        logo_png.parent.mkdir(parents=True, exist_ok=True)
        img.save(logo_png)
        info(f"로고 원본 {src} → {logo_png} ({img.width}x{img.height}px)")
        return logo_png, "source"
    if src is not None:
        warn(f"로고 원본이 없습니다: {src}")
    if logo_png.exists():
        warn(f"저장소에 있는 {logo_png.name} 를 그대로 씁니다.")
        return logo_png, "cached"
    placeholder = assets / PLACEHOLDER_NAME
    if not placeholder.exists():
        make_placeholder(placeholder)
    warn(f"로고가 없어 자리표시 이미지({placeholder.name})로 대체합니다.")
    return placeholder, "placeholder"


def compose_footer(logo_png: Path, out: Path, width_mm: float = PRINT_WIDTH_MM, dpi: int = FOOTER_DPI) -> Path:
    """바닥글 합성 PNG: 굵은 가로선 + 작은 로고(5mm) + 회사명.

    폭은 본문 A~Z 의 실제 인쇄 폭(width_mm)과 같게 만들어, 머리글 선·본문·바닥글 선의 양 끝을 맞춘다.
    """
    width = mm_to_px(width_mm, dpi)
    rule_h = max(1, mm_to_px(RULE_MM, dpi))
    gap = mm_to_px(1.3, dpi)
    logo_h = mm_to_px(FOOTER_LOGO_MM, dpi)
    pad_bottom = mm_to_px(0.4, dpi)
    height = rule_h + gap + logo_h + pad_bottom

    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, 0, width - 1, rule_h - 1], fill=RULE_RGB)

    with Image.open(logo_png) as src:
        logo = src.convert("RGBA")
    if logo.height > logo_h:
        logo = logo.resize((max(1, round(logo.width * logo_h / logo.height)), logo_h), Image.Resampling.LANCZOS)
    # 원본이 5mm@300dpi 보다 작으면 늘리지 않고(업스케일 금지) 세로 가운데에 둔다
    logo_top = rule_h + gap + (logo_h - logo.height) // 2
    canvas.paste(logo, (0, logo_top), logo)

    pt_to_px = dpi / 72.0
    mark_font = ImageFont.truetype(str(FONT_BOLD), round(9.5 * pt_to_px))
    text_font = ImageFont.truetype(str(FONT_BOLD), round(7.0 * pt_to_px))
    cap_top = mark_font.getbbox("S", anchor="ls")[1]  # 음수: 기준선 위 대문자 높이
    baseline = rule_h + gap + logo_h / 2 - cap_top / 2
    x = logo.width + mm_to_px(1.5, dpi)
    d.text((x, baseline), COMPANY_MARK, fill=(0, 0, 0), font=mark_font, anchor="ls")
    x += d.textlength(COMPANY_MARK, font=mark_font)
    d.text((x, baseline), COMPANY_TEXT, fill=(0, 0, 0), font=text_font, anchor="ls")

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, dpi=(dpi, dpi))
    return out


def compose_header(logo_png: Path, out: Path, dpi: int = FOOTER_DPI) -> Path:
    """왼쪽 머리글 합성 PNG: 로고(높이 10mm) + 문서명(맑은 고딕 굵게 9pt). 300dpi.

    로고는 원본보다 크게 늘리지 않는다(128px → 10mm@300dpi = 118px 로 줄임). 문서명은 로고 세로 가운데.
    """
    logo_h = mm_to_px(HEADER_LOGO_MM, dpi)
    with Image.open(logo_png) as src:
        logo = src.convert("RGBA")
    if logo.height > logo_h:
        logo = logo.resize((max(1, round(logo.width * logo_h / logo.height)), logo_h), Image.Resampling.LANCZOS)
    font = ImageFont.truetype(str(FONT_BOLD), round(TITLE_PT * dpi / 72.0))
    gap = mm_to_px(TITLE_GAP_MM, dpi)
    left, top, right, bottom = font.getbbox(DOC_TITLE, anchor="lm")
    width = logo.width + gap + int(right) + 2
    canvas = Image.new("RGB", (width, logo_h), (255, 255, 255))
    canvas.paste(logo, (0, (logo_h - logo.height) // 2), logo)
    ImageDraw.Draw(canvas).text((logo.width + gap, logo_h / 2), DOC_TITLE, fill=(0, 0, 0), font=font, anchor="lm")
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, dpi=(dpi, dpi))
    return out


# ---------------------------------------------------------------- VBA 원본


@dataclass(frozen=True)
class VbaSources:
    header_sync_bas: str
    this_workbook: str
    settings_sheet: str


def load_vba_sources(vba_dir: Path = VBA_DIR) -> VbaSources:
    def read(name: str) -> str:
        return (vba_dir / name).read_text(encoding="utf-8")

    return VbaSources(read("HeaderSync.bas"), read("ThisWorkbook.vba"), read("SettingsSheet.vba"))


def to_crlf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\n", "\r\n")


# ---------------------------------------------------------------- AccessVBOM (읽기 전용)

VBOM_PLACES = ("HKCU\\Policies", "HKLM\\Policies", "HKCU", "HKLM")  # 앞쪽이 우선


def read_access_vbom(version: str) -> dict[str, int | None]:
    """AccessVBOM 값을 레지스트리에서 읽기만 한다(쓰기 없음). 키·값이 없으면 None."""
    import winreg

    bases = {
        "HKCU\\Policies": (winreg.HKEY_CURRENT_USER, r"Software\Policies\Microsoft\Office"),
        "HKLM\\Policies": (winreg.HKEY_LOCAL_MACHINE, r"Software\Policies\Microsoft\Office"),
        "HKCU": (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Office"),
        "HKLM": (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Office"),
    }
    found: dict[str, int | None] = {}
    for label in VBOM_PLACES:
        hive, base = bases[label]
        try:
            with winreg.OpenKey(hive, rf"{base}\{version}\Excel\Security", 0, winreg.KEY_READ) as key:
                found[label] = int(winreg.QueryValueEx(key, "AccessVBOM")[0])
        except OSError:
            found[label] = None
    return found


def effective_access_vbom(values: dict[str, int | None]) -> int:
    for label in VBOM_PLACES:
        if values.get(label) is not None:
            return int(values[label])
    return 0


def describe_vbom(values: dict[str, int | None]) -> str:
    return ", ".join(f"{k}={'없음' if v is None else v}" for k, v in values.items())


VBOM_STOP_MESSAGE = (
    "[중단] Excel 의 'VBA 프로젝트 개체 모델에 안전하게 액세스' 설정이 꺼져 있습니다.\n"
    "  이 스크립트는 보안 설정을 바꾸지 않습니다. 계속하려면 다음 중 하나를 하세요.\n"
    "  1) Excel > 파일 > 옵션 > 보안 센터 > 보안 센터 설정 > 매크로 설정 에서\n"
    "     'VBA 프로젝트 개체 모델에 안전하게 액세스'를 직접 켠 뒤 다시 실행하고, 끝나면 다시 끕니다.\n"
    "  2) README 의 '매크로 직접 가져오기' 절차대로 vba/ 파일을 손으로 넣습니다."
)


# ---------------------------------------------------------------- Excel COM

# Excel 이 바쁠 때 돌려주는 "호출 거부" 계열 오류. 이 경우 호출 자체가 실행되지 않았으므로 다시 시도해도 안전하다.
_BUSY_HRESULTS = {
    -2147418111,  # RPC_E_CALL_REJECTED
    -2147417846,  # RPC_E_SERVERCALL_RETRYLATER
    -2146777998,  # 0x800AC472 VBA_E_IGNORE (Excel 초기화·편집 중)
}


_ACTIVE_EXCEL_PID: int | None = None


class ExcelBlockedError(RuntimeError):
    """Excel 이 대화상자(정품 인증 마법사 등) 때문에 자동화 호출에 응답하지 않는다."""


def visible_windows(pid: int) -> list[str]:
    """해당 프로세스의 보이는 창 제목 목록 (막고 있는 대화상자 진단용)."""
    import win32gui
    import win32process

    titles: list[str] = []

    def cb(hwnd, _):
        if win32process.GetWindowThreadProcessId(hwnd)[1] == pid and win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                titles.append(title)

    win32gui.EnumWindows(cb, None)
    return titles


ACTIVATION_WAIT = 300.0  # 인증 마법사가 떠 있으면 사용자가 닫을 때까지 기다리는 시간(초)
_ACTIVATION_NOTICE_SHOWN = False


def _activation_dialog_open() -> bool:
    if not _ACTIVE_EXCEL_PID:
        return False
    try:
        return any("인증" in t or "Activation" in t for t in visible_windows(_ACTIVE_EXCEL_PID))
    except Exception:
        return False


def _retry(fn, timeout: float = 60.0):
    import pywintypes

    global _ACTIVATION_NOTICE_SHOWN
    start = time.monotonic()
    deadline = start + timeout
    while True:
        try:
            return fn()
        except pywintypes.com_error as e:
            if e.args[0] not in _BUSY_HRESULTS:
                raise
            if time.monotonic() - start > 3 and _activation_dialog_open():
                # Office 정품 인증 마법사는 사용자가 직접 닫는다(스크립트가 누르지 않음). 닫힐 때까지 기다린다.
                if not _ACTIVATION_NOTICE_SHOWN:
                    print(
                        "[안내] 'Microsoft Office 인증 마법사' 창이 떠 있어 Excel 이 멈춰 있습니다. "
                        f"창에서 [닫기]를 눌러 주세요. 최대 {ACTIVATION_WAIT / 60:.0f}분 기다립니다.",
                        file=sys.stderr,
                        flush=True,
                    )
                    _ACTIVATION_NOTICE_SHOWN = True
                deadline = max(deadline, start + ACTIVATION_WAIT)
            if time.monotonic() > deadline:
                shown = visible_windows(_ACTIVE_EXCEL_PID) if _ACTIVE_EXCEL_PID else []
                raise ExcelBlockedError(
                    f"Excel 이 {timeout:.0f}초 동안 자동화 호출을 거부했습니다. "
                    f"화면에 떠 있는 Excel 창: {shown or '없음'}. "
                    "'Microsoft Office 인증 마법사' 같은 대화상자가 떠 있으면 Office 정품 인증을 먼저 해결해야 합니다."
                ) from e
            time.sleep(0.2)


def _unwrap(v):
    return v._obj if isinstance(v, Com) else v


def _wrap(v):
    from win32com.client import CDispatch

    if isinstance(v, CDispatch):
        return Com(v)
    if callable(v):  # 동적 디스패치의 메서드 / 인자 있는 속성(Range("A1"), Borders(9) 등)
        return lambda *a, **k: _wrap(_retry(lambda: v(*map(_unwrap, a), **{n: _unwrap(x) for n, x in k.items()})))
    return v


class Com:
    """COM 객체 프록시: 모든 속성 읽기/쓰기·호출을 '호출 거부' 시 재시도한다."""

    __slots__ = ("_obj",)

    def __init__(self, obj) -> None:
        object.__setattr__(self, "_obj", obj)

    @staticmethod
    def _retry_attr(name: str, fn):
        # 동적 디스패치는 이름 조회 중 '호출 거부'를 AttributeError 로 바꿔 내보내므로 잠깐 재시도한다
        deadline = time.monotonic() + 10.0
        while True:
            try:
                return _retry(fn)
            except AttributeError:
                if name.startswith("_") or time.monotonic() > deadline:
                    raise
                time.sleep(0.2)

    def __getattr__(self, name: str):
        return _wrap(self._retry_attr(name, lambda: getattr(self._obj, name)))

    def __setattr__(self, name: str, value) -> None:
        self._retry_attr(name, lambda: setattr(self._obj, name, _unwrap(value)))

    def __call__(self, *a, **k):
        return _wrap(_retry(lambda: self._obj(*map(_unwrap, a), **{n: _unwrap(x) for n, x in k.items()})))

    def __iter__(self):
        for item in _retry(lambda: list(self._obj)):
            yield _wrap(item)


def _process_alive(pid: int) -> bool:
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return False
    try:
        code = ctypes.c_ulong()
        k32.GetExitCodeProcess(h, ctypes.byref(code))
        return code.value == STILL_ACTIVE
    finally:
        k32.CloseHandle(h)


def _wait_or_kill(pid: int, timeout: float = 15.0) -> None:
    """Quit 후에도 남아 있는 자동화 인스턴스(이 스크립트가 띄운 PID)만 강제 종료한다."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _process_alive(pid):
            return
        time.sleep(0.3)
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
    if h:
        k32.TerminateProcess(h, 1)
        k32.CloseHandle(h)
        warn(f"Excel 자동화 인스턴스(PID {pid})가 종료되지 않아 강제로 닫았습니다.")


class ExcelSession:
    """자동화용 Excel 인스턴스를 따로 띄우고, 끝나면 그 인스턴스만 정리한다.

    사용자가 열어 둔 Excel 창에는 붙지 않는다(DispatchEx = 새 프로세스).
    """

    def __init__(self) -> None:
        import win32com.client

        self.xl = Com(win32com.client.DispatchEx("Excel.Application"))
        self._wait_ready()
        self.pid = self._pid()
        global _ACTIVE_EXCEL_PID
        _ACTIVE_EXCEL_PID = self.pid
        self.xl.Visible = False
        self.xl.DisplayAlerts = False
        self.xl.ScreenUpdating = False

    def _pid(self) -> int | None:
        try:
            import win32process

            return win32process.GetWindowThreadProcessId(self.xl.Hwnd)[1]
        except Exception:
            return None

    def _wait_ready(self, timeout: float = 60.0) -> None:
        """방금 띄운 Excel 은 초기화 중에 호출을 거부하므로 응답할 때까지 기다린다."""
        deadline = time.monotonic() + timeout
        while True:
            try:
                _ = self.xl.Version
                _ = self.xl.Workbooks.Count
                return
            except Exception:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.5)

    def quit(self) -> None:
        import gc

        if self.xl is None:
            return
        try:
            while self.xl.Workbooks.Count:
                self.xl.Workbooks(1).Close(False)
        except Exception:
            pass
        try:
            self.xl.Quit()
        except Exception:
            pass
        self.xl = None
        gc.collect()  # 남은 COM 참조를 풀어야 Excel 프로세스가 스스로 끝난다
        if self.pid:
            _wait_or_kill(self.pid)

    def __enter__(self) -> "ExcelSession":
        return self

    def __exit__(self, *exc) -> None:
        self.quit()


def snapped_widths(ws, max_pt: float) -> list[tuple[float, float]]:
    """Excel 이 실제로 받아들이는 열 너비 값들을 (ColumnWidth, 화면 폭 pt) 로, 큰 것부터 돌려준다.

    열 너비는 기본 글꼴과 화면 픽셀에 맞춰 끊기므로(96dpi 에서 0.75pt 단위) 값을 넣어 보고 다시 읽는다.
    """
    col = ws.Columns(1)
    seen: dict[float, float] = {}
    cw = 1.0
    while cw <= 8.0:
        col.ColumnWidth = cw
        width = float(col.Width)
        if width > max_pt + 1e-6:
            break
        seen.setdefault(float(col.ColumnWidth), width)
        cw = round(cw + 0.05, 2)
    return sorted(seen.items(), key=lambda kv: kv[1], reverse=True)


@dataclass(frozen=True)
class PrintFit:
    column_width: float  # ColumnWidth (글자 단위)
    screen_pt: float  # 화면 폭 (열 하나)
    print_pt: float  # PDF 에 찍힌 폭 (열 하나, 100%)
    span_mm: float  # PDF 에 찍힌 A~Z 전체 폭 (100%)
    tried: tuple  # (ColumnWidth, 페이지 수, A~Z mm) 시도 기록


def vertical_lines_pt(pdf: Path) -> tuple[int, list[float]]:
    """PDF 첫 페이지의 세로 테두리 x 좌표(pt)와 페이지 수."""
    import pymupdf

    with pymupdf.open(pdf) as doc:
        xs = sorted(
            {round((d["rect"].x0 + d["rect"].x1) / 2, 2) for d in doc[0].get_drawings() if d["rect"].width < 2 and d["rect"].height > 5}
        )
        return doc.page_count, xs


def calibrate_print_width(ws, xl, workdir: Path) -> PrintFit:
    """100% 배율로 PDF 를 내보내 실측해서, A~Z 가 인쇄 폭(180mm) 한 장에 들어가는 가장 큰 열 너비를 고른다.

    Excel 은 인쇄(PDF 내보내기 포함) 때 기본 프린터 기준 글꼴 폭으로 열을 다시 재므로
    화면 폭보다 넓게 찍힌다(이 PC 실측 약 5%). 그래서 화면 계산값이 아니라 PDF 실측으로 맞춘다.
    """
    limit_pt = mm_to_pt(PRINT_WIDTH_MM)
    marks = ws.Range("A2:Z2")
    ps = ws.PageSetup
    tried = []
    try:
        for edge in (7, 10, 11):  # 왼쪽 / 오른쪽 / 안쪽 세로 테두리로 열 경계를 PDF 에 표시
            marks.Borders(edge).LineStyle = XL_CONTINUOUS
            marks.Borders(edge).Weight = 1
        ps.Zoom = 100
        for cw, screen_pt in snapped_widths(ws, limit_pt / N_COLS):
            ws.Range("A:Z").ColumnWidth = cw
            pdf = workdir / f"calib_{cw}.pdf"
            ws.ExportAsFixedFormat(0, str(pdf))
            pages, xs = vertical_lines_pt(pdf)
            span = xs[-1] - xs[0] if len(xs) >= 2 else float("inf")
            tried.append((cw, pages, round(span / mm_to_pt(1), 2)))
            if pages == 1 and span <= limit_pt + 0.01:
                return PrintFit(cw, screen_pt, span / N_COLS, span / mm_to_pt(1), tuple(tried))
        raise RuntimeError(f"A~Z 를 100% 배율로 한 장 폭에 넣을 수 있는 열 너비가 없습니다: {tried}")
    finally:
        marks.Borders.LineStyle = -4142  # xlNone
        ps.Zoom = False
        ps.FitToPagesWide = 1
        ps.FitToPagesTall = False


def setup_settings_sheet(ws) -> None:
    ws.Name = SETTINGS_SHEET
    ws.Columns("A").ColumnWidth = 2
    ws.Columns("B").ColumnWidth = 14
    ws.Columns("C").ColumnWidth = 56

    title = ws.Range("B2")
    title.Value = "구조계산서 양식 — 설정"
    title.Font.Bold = True
    title.Font.Size = 14

    for addr, text in {"B4": "프로젝트명", "B5": "작성일"}.items():
        ws.Range(addr).Value = text
        ws.Range(addr).Font.Bold = True

    for addr in ("C4", "C5"):
        cell = ws.Range(addr)
        cell.Interior.Color = 0xCCF2FF  # 연한 노랑 (Excel 색은 BGR)
        for edge in (7, 8, 9, 10):  # 왼/위/아래/오른쪽
            cell.Borders(edge).LineStyle = XL_CONTINUOUS
            cell.Borders(edge).Color = 0x999999
    ws.Range("C5").NumberFormat = "yyyy.mm.dd"
    ws.Range("C5").HorizontalAlignment = -4131  # 왼쪽 정렬

    wb = ws.Parent
    wb.Names.Add(Name="PROJECT_NAME", RefersTo=f"='{SETTINGS_SHEET}'!$C$4")
    wb.Names.Add(Name="DOC_DATE", RefersTo=f"='{SETTINGS_SHEET}'!$C$5")

def settings_notes(max_chars: int) -> list[str]:
    return [
        "· 노란 칸에 프로젝트명과 작성일을 적으면 모든 계산서 시트의 머리글(오른쪽 위)에 자동으로 들어갑니다.",
        f"· 프로젝트명은 {max_chars}자 이내로 적으세요. 길면 머리글 글씨가 자동으로 작아집니다(9 → 8 → 7pt).",
        "· 작성일은 2026-11-04 처럼 날짜로 입력하세요. 비워 두면 머리글에 페이지 번호만 나옵니다.",
        "· 이 시트는 인쇄하지 않습니다. 계산서 시트만 골라서 인쇄·PDF 저장하세요.",
        "· 계산서를 여러 장 쓰려면 '계산서' 시트 탭을 Ctrl 누른 채 끌거나 [이동/복사]로 복사하세요.",
        "· 머리글 자동 반영은 매크로를 허용해야 동작합니다. 허용하지 않으면 마지막 저장 상태의 머리글이 나옵니다.",
    ]


def finalize_settings_sheet(ws, max_chars: int) -> None:
    """프로젝트명 글자 수 상한(7pt 로 들어가는 최대 글자 수, build 실측)으로 안내문·유효성 검사·인쇄 영역을 마무리."""
    notes = settings_notes(max_chars)
    for i, text in enumerate(notes):
        cell = ws.Range(f"B{NOTES_FIRST_ROW + i}")
        cell.Value = text
        cell.Font.Size = 9
        cell.Font.Color = 0x555555

    v = ws.Range("C4").Validation
    v.Delete()
    v.Add(Type=6, AlertStyle=1, Operator=8, Formula1=str(max_chars))  # 텍스트 길이 ≤ N, 중지
    v.ErrorTitle = "프로젝트명이 너무 깁니다"
    v.ErrorMessage = (
        f"프로젝트명은 {max_chars}자 이하로 입력하세요. (머리글 오른쪽에 7pt 로 들어갈 수 있는 최대 길이)"
    )
    v.InputTitle = "프로젝트명"
    v.InputMessage = f"{max_chars}자 이하. 길면 머리글 글씨가 자동으로 작아집니다."
    v.ShowError = True

    # 실수로 같이 인쇄돼도 1장으로 끝나도록 인쇄 영역을 안내문까지만
    ws.PageSetup.PrintArea = f"$B$2:$C${NOTES_FIRST_ROW + len(notes) - 1}"


@dataclass(frozen=True)
class CalcLayout:
    fit: PrintFit
    margin_lr_mm: float  # 좌우 여백 = (210 - A~Z 실측 폭) / 2
    footer_width_mm: float  # 바닥글 합성 이미지 폭 = A~Z 실측 폭
    pictures: dict  # 머리글/바닥글 그림 인쇄 늘어남 실측과 보정값
    text: dict  # 프로젝트명 글꼴 단계별 글자 수 경계 (PDF 실측)


def setup_calc_sheet(ws, xl, logo_png: Path, header_png: Path, footer_png: Path) -> CalcLayout:
    """계산서 시트: 인쇄 제목 행 선, 페이지 설정, 머리글 로고, 열 너비(PDF 실측), 여백, 바닥글 이미지.

    열 너비를 먼저 실측으로 고른 뒤, 그 A~Z 폭에 맞춰 좌우 여백과 바닥글 이미지 폭을 정한다
    → 머리글 선(1행 테두리)·본문·바닥글 선의 왼쪽/오른쪽 끝이 같은 위치에 온다.
    """
    ws.Name = CALC_SHEET

    # 인쇄 제목 행(1행): 낮게 + 굵은 아래 테두리 → 모든 장에서 머리글 아래 가로선으로 반복
    ws.Rows(1).RowHeight = 4
    border = ws.Range("A1:Z1").Borders(XL_EDGE_BOTTOM)
    border.LineStyle = XL_CONTINUOUS
    border.Weight = XL_THICK
    r, g, b = RULE_RGB
    border.Color = r + g * 256 + b * 65536

    ps = ws.PageSetup
    xl.PrintCommunication = False
    try:
        ps.PaperSize = XL_PAPER_A4
        ps.Orientation = XL_PORTRAIT
        ps.LeftMargin = mm_to_pt(PAGE_MARGIN_LR)
        ps.RightMargin = mm_to_pt(PAGE_MARGIN_LR)
        ps.TopMargin = mm_to_pt(PAGE_MARGIN_TOP)
        ps.BottomMargin = mm_to_pt(PAGE_MARGIN_BOTTOM)
        ps.HeaderMargin = mm_to_pt(HEADER_MARGIN)
        ps.FooterMargin = mm_to_pt(FOOTER_MARGIN)
        ps.CenterHorizontally = False  # 여백을 실측 폭에 맞추므로 가운데 정렬은 쓰지 않는다
        ps.Zoom = False
        ps.FitToPagesWide = 1
        ps.FitToPagesTall = False
        ps.PrintArea = "$A:$Z"
        ps.PrintTitleRows = "$1:$1"
        ps.PrintGridlines = False
        ps.FirstPageNumber = XL_AUTOMATIC
        ps.ScaleWithDocHeaderFooter = False
        ps.AlignMarginsHeaderFooter = True
    finally:
        xl.PrintCommunication = True

    # 왼쪽 머리글: 로고 + 문서명 합성 이미지(높이 10mm, 가로세로 비율 고정). 가운데 머리글은 비움(D4-2)
    compose_header(logo_png, header_png)
    with Image.open(header_png) as img:
        header_target = (HEADER_LOGO_MM * img.width / img.height, HEADER_LOGO_MM)
    info(f"머리글 합성 이미지 → {header_png} ({header_target[0]:.2f}×{header_target[1]:.2f}mm)")
    hp = ps.LeftHeaderPicture
    hp.Filename = str(header_png)
    hp.LockAspectRatio = -1
    hp.Height = mm_to_pt(HEADER_LOGO_MM)
    ps.LeftHeader = "&G"
    ps.CenterHeader = ""

    # A~Z 열 너비: 같은 너비로, 100% 배율 PDF 실측이 180mm(여백 15mm 기준) 한 장에 들어가는 최댓값
    with tempfile.TemporaryDirectory() as tmp:
        fit = calibrate_print_width(ws, xl, Path(tmp))
    ws.Range("A:Z").ColumnWidth = fit.column_width

    # 좌우 여백을 실측 A~Z 폭에 맞춘다. 여유가 0 이면 반올림 오차로 Z열이 넘쳐 맞춤 기능이 배율을 줄이므로
    # (실측: 0.01mm 초과로 98% 축소) 오른쪽에 MARGIN_SLACK_MM*2 만큼 여유를 둔다. 왼쪽 끝 정렬에는 영향 없음.
    margin = (210.0 - fit.span_mm) / 2 - MARGIN_SLACK_MM
    ps.LeftMargin = mm_to_pt(margin)
    ps.RightMargin = mm_to_pt(margin)

    # 바닥글: 선 + 작은 로고 + 회사명 합성 이미지, 폭 = A~Z 실측 폭 (가로세로 비율 고정)
    compose_footer(logo_png, footer_png, width_mm=fit.span_mm)
    info(f"바닥글 합성 이미지 → {footer_png} (폭 {fit.span_mm:.2f}mm)")
    fp = ps.LeftFooterPicture
    fp.Filename = str(footer_png)
    fp.LockAspectRatio = -1
    fp.Width = mm_to_pt(fit.span_mm)
    ps.LeftFooter = "&G"

    with Image.open(footer_png) as img:
        footer_target = (fit.span_mm, fit.span_mm * img.height / img.width)
    with tempfile.TemporaryDirectory() as tmp:
        pics = calibrate_pictures(ws, Path(tmp), margin, header_target, footer_target)
        text = measure_project_capacity(ws, Path(tmp), pics["header"]["result_bbox_mm"][2])
    return CalcLayout(fit, margin, fit.span_mm, pics, text)


def _pdf_lines(pdf: Path) -> list[tuple[str, tuple]]:
    """PDF 첫 페이지의 글줄 (글자, bbox mm)."""
    import pymupdf

    mm1 = mm_to_pt(1)
    lines = []
    with pymupdf.open(pdf) as doc:
        for b in doc[0].get_text("dict")["blocks"]:
            for line in b.get("lines", []):
                text = "".join(s["text"] for s in line["spans"])
                if text.strip():
                    lines.append((text, tuple(v / mm1 for v in line["bbox"])))
    return lines


def measure_project_capacity(ws, workdir: Path, header_img_right_mm: float) -> dict:
    """프로젝트명이 9/8/7pt 에서 몇 글자까지 들어가는지 PDF 실측으로 정한다(D4-2).

    - 한글 한 글자 폭: 오른쪽 머리글에 "가"×20 을 각 크기로 찍어 잰다(인쇄 때 넓게 찍히는 것까지 포함).
    - 영문·숫자·공백 가중치: 같은 크기의 ASCII 견본 한 글자 평균 폭 ÷ 한글 폭 (0.05 단위 올림).
    - 들어갈 폭: 오른쪽 머리글 글줄의 실제 오른쪽 끝 − (머리글 이미지 오른쪽 끝 + 3mm).
    - 단계별 경계(가중 글자 수) = 들어갈 폭 ÷ 한글 폭 − 0.5 (0.1 단위 내림, 반 글자 여유).
    """
    import math

    ps = ws.PageSetup
    probe = "가" * 20
    per_char: dict[int, float] = {}
    ascii_ratio: list[float] = []
    text_right = None
    for pt in PROJECT_SIZES:
        # 1행 = 한글 견본, 2행 = ASCII 견본 (같은 크기·굵게, 오른쪽 정렬)
        ps.RightHeader = f'&{pt}&"맑은 고딕,Bold"{probe}\n&{pt}&"맑은 고딕,Bold"{ASCII_SAMPLE}'
        pdf = workdir / f"text_{pt}.pdf"
        ws.ExportAsFixedFormat(0, str(pdf))
        lines = _pdf_lines(pdf)
        hl = next(bb for t, bb in lines if t.strip() == probe)
        al = next(bb for t, bb in lines if t.strip() == ASCII_SAMPLE)
        per_char[pt] = (hl[2] - hl[0]) / len(probe)
        ascii_ratio.append(((al[2] - al[0]) / len(ASCII_SAMPLE)) / per_char[pt])
        text_right = hl[2]
    ps.RightHeader = ""
    weight = math.ceil(max(ascii_ratio) * 20 - 1e-9) / 20
    avail = text_right - (header_img_right_mm + PROJECT_GAP_MM)
    caps = {pt: math.floor((avail / per_char[pt] - 0.5) * 10) / 10 for pt in PROJECT_SIZES}
    max_chars = int(math.floor(caps[min(PROJECT_SIZES)]))
    info(
        "프로젝트명 폭 실측: 한글 한 글자 "
        + ", ".join(f"{pt}pt {per_char[pt]:.3f}mm" for pt in PROJECT_SIZES)
        + f" / 영문·숫자·공백 가중치 {weight:.2f} (실측 {', '.join(f'{r:.3f}' for r in ascii_ratio)})"
    )
    info(
        f"프로젝트명 들어갈 폭 {avail:.2f}mm (머리글 이미지 오른쪽 끝 {header_img_right_mm:.2f}mm + {PROJECT_GAP_MM}mm"
        f" ~ 머리글 글줄 오른쪽 끝 {text_right:.2f}mm) → 글자 수 경계 "
        + ", ".join(f"{pt}pt ≤ {caps[pt]}" for pt in PROJECT_SIZES)
        + f", 입력 상한 {max_chars}자"
    )
    return {
        "per_char_mm": per_char,
        "ascii_ratio": ascii_ratio,
        "ascii_weight": weight,
        "avail_mm": avail,
        "text_right_mm": text_right,
        "caps": caps,
        "max_chars": max_chars,
    }


def _pdf_pictures(pdf: Path) -> dict:
    """PDF 첫 페이지의 머리글 그림 / 바닥글 그림 위치(mm)와 페이지 크기(mm)."""
    import pymupdf

    with pymupdf.open(pdf) as doc:
        page = doc[0]
        mm1 = mm_to_pt(1)
        out = {"page_mm": (page.rect.width / mm1, page.rect.height / mm1), "pages": doc.page_count}
        for info_ in page.get_image_info():
            x0, y0, x1, y1 = (v / mm1 for v in info_["bbox"])
            item = {"bbox": (x0, y0, x1, y1), "size": (x1 - x0, y1 - y0), "pixels": (info_["width"], info_["height"])}
            if y1 < 40:
                out["header"] = item
            elif y0 > 250:
                out["footer"] = item
        return out


def calibrate_pictures(ws, workdir: Path, margin_mm: float, logo_mm: tuple, footer_mm: tuple) -> dict:
    """머리글 로고·바닥글 이미지가 PDF 에 실제로 찍힌 크기를 재서, 늘어난 비율만큼 미리 줄여 지정한다.

    Excel 은 인쇄할 때 기본 프린터 기준으로 머리글/바닥글 그림을 가로·세로 다른 비율로 늘려 찍는다
    (이 PC 실측 약 1.05 × 1.10). 가로세로 비율 고정을 풀고 Width ÷ 가로비율, Height ÷ 세로비율로 지정한 뒤
    한 번 더 내보내 확인한다. 기준을 못 맞추면 반복하지 않고 경고와 실측값만 남긴다.
    """
    ps = ws.PageSetup
    pics = {"header": ps.LeftHeaderPicture, "footer": ps.LeftFooterPicture}
    targets = {"header": logo_mm, "footer": footer_mm}

    def export(tag: str) -> dict:
        pdf = workdir / f"pictures_{tag}.pdf"
        ws.ExportAsFixedFormat(0, str(pdf))
        got = _pdf_pictures(pdf)
        if abs(got["page_mm"][0] - 210.0) > 0.5:
            warn(f"PDF 페이지 폭이 {got['page_mm'][0]:.2f}mm 입니다(배율이 100%가 아님). 그림 실측이 부정확할 수 있습니다.")
        for key in ("header", "footer"):
            if key not in got:
                raise RuntimeError(f"PDF 에서 {key} 그림을 찾지 못했습니다: {got}")
        return got

    first = export("before")
    record: dict = {"page_mm": first["page_mm"]}
    for key, pic in pics.items():
        stored = (float(pic.Width) / mm_to_pt(1), float(pic.Height) / mm_to_pt(1))
        printed = first[key]["size"]
        ratio = (printed[0] / stored[0], printed[1] / stored[1])
        want = targets[key]
        pic.LockAspectRatio = 0  # msoFalse: 가로·세로를 따로 지정
        pic.Width = mm_to_pt(want[0] / ratio[0])
        pic.Height = mm_to_pt(want[1] / ratio[1])
        record[key] = {
            "stored_mm": stored,
            "printed_mm": printed,
            "stretch": ratio,
            "set_mm": (float(pic.Width) / mm_to_pt(1), float(pic.Height) / mm_to_pt(1)),
        }

    # 보정한 크기를 반영하려면 그림 코드(&G)를 다시 써 준다
    ps.LeftHeader = "&G"
    ps.LeftFooter = "&G"
    after = export("after")
    h, f = after["header"], after["footer"]
    record["header"]["result_mm"] = h["size"]
    record["header"]["result_bbox_mm"] = h["bbox"]
    record["header"]["result_pixels"] = h["pixels"]
    record["footer"]["result_bbox_mm"] = f["bbox"]
    body = (margin_mm, margin_mm + footer_mm[0])
    want_h = targets["header"]
    checks = {
        # 머리글 이미지는 로고(정사각형) + 문서명이라, 이미지 전체 비율이 원본 비율과 같으면 로고도 1:1
        "logo_aspect": (h["size"][0] / h["size"][1]) / (want_h[0] / want_h[1]),
        "logo_height_mm": h["size"][1],
        "header_left_diff_mm": h["bbox"][0] - body[0],
        "footer_left_diff_mm": f["bbox"][0] - body[0],
        "footer_right_diff_mm": f["bbox"][2] - body[1],
    }
    checks["pass"] = (
        abs(checks["logo_aspect"] - 1.0) <= 0.02
        and abs(checks["logo_height_mm"] - HEADER_LOGO_MM) <= 0.3
        and abs(checks["header_left_diff_mm"]) <= 0.5
        and abs(checks["footer_left_diff_mm"]) <= 0.5
        and abs(checks["footer_right_diff_mm"]) <= 0.5
    )
    record["checks"] = checks
    for key in ("header", "footer"):
        r = record[key]
        info(
            f"그림 보정[{key}] 저장 {r['stored_mm'][0]:.2f}×{r['stored_mm'][1]:.2f}mm → 인쇄 "
            f"{r['printed_mm'][0]:.2f}×{r['printed_mm'][1]:.2f}mm, 늘어난 비율 가로 {r['stretch'][0]:.4f} / "
            f"세로 {r['stretch'][1]:.4f} → 지정 {r['set_mm'][0]:.2f}×{r['set_mm'][1]:.2f}mm"
        )
    info(
        f"그림 보정 확인: 머리글 이미지 {h['bbox'][0]:.2f}~{h['bbox'][2]:.2f}mm, {h['size'][0]:.2f}×{h['size'][1]:.2f}mm "
        f"(비율 {checks['logo_aspect']:.3f}, 왼쪽 끝 차이 {checks['header_left_diff_mm']:+.2f}mm, "
        f"PDF 안 {h['pixels'][0]}×{h['pixels'][1]}px), 바닥글 {f['bbox'][0]:.2f}~{f['bbox'][2]:.2f}mm "
        f"(본문 {body[0]:.2f}~{body[1]:.2f}mm, 차이 {checks['footer_left_diff_mm']:+.2f}/{checks['footer_right_diff_mm']:+.2f}mm)"
    )
    if not checks["pass"]:
        warn(
            "그림 보정 결과가 기준(로고 비율 1.00±0.02·높이 10±0.3mm, 머리글·바닥글 끝 ±0.5mm)을 벗어났습니다. 실측값을 확인하세요."
        )
    return record


def find_document_component(vbp, sheet_name: str):
    for comp in vbp.VBComponents:
        if comp.Type != VBEXT_CT_DOCUMENT:
            continue
        try:
            if comp.Properties("Name").Value == sheet_name:
                return comp
        except Exception:
            continue
    raise RuntimeError(f"VBA 프로젝트에서 '{sheet_name}' 시트 모듈을 찾지 못했습니다.")


def replace_module_code(comp, code: str) -> None:
    cm = comp.CodeModule
    if cm.CountOfLines:
        cm.DeleteLines(1, cm.CountOfLines)  # VBE 설정에 따라 자동으로 붙는 Option Explicit 중복 방지
    cm.AddFromString(to_crlf(code))


def inject_vba_constants(bas: str, text: dict) -> str:
    """HeaderSync.bas 의 실측 상수(CAP_9PT/CAP_8PT/CAP_7PT/ASCII_WEIGHT) 값을 build 실측값으로 바꾼다."""
    import re

    values = {f"CAP_{pt}PT": text["caps"][pt] for pt in PROJECT_SIZES}
    values["ASCII_WEIGHT"] = text["ascii_weight"]
    for name, value in values.items():
        pattern = rf"(Private Const {name} As Double = )[0-9.]+"
        if not re.search(pattern, bas):
            raise RuntimeError(f"HeaderSync.bas 에 상수 {name} 가 없습니다.")
        bas = re.sub(pattern, lambda m: f"{m.group(1)}{value:.2f}", bas)
    return bas


def install_vba(wb, sources: VbaSources, text: dict) -> None:
    vbp = wb.VBProject  # 신뢰 설정이 꺼져 있으면 여기서 오류
    with tempfile.TemporaryDirectory() as tmp:
        bas = Path(tmp) / "HeaderSync.bas"
        # VBE 가져오기는 시스템 ANSI 코드페이지(한국어 Windows = CP949)로 읽는다
        code = inject_vba_constants(sources.header_sync_bas, text)
        bas.write_bytes(to_crlf(code).encode("mbcs"))
        vbp.VBComponents.Import(str(bas))
    replace_module_code(vbp.VBComponents(wb.CodeName), sources.this_workbook)
    replace_module_code(find_document_component(vbp, SETTINGS_SHEET), sources.settings_sheet)


def _build_workbook(
    xl, logo_png: Path, header_png: Path, footer_png: Path, sources: VbaSources, save_to: Path
) -> dict:
    xl.EnableEvents = False
    try:
        wb = xl.Workbooks.Add(XL_WBA_WORKSHEET)
        normal = wb.Styles("Normal").Font
        normal.Name = "맑은 고딕"
        normal.Size = 10
        settings = wb.Worksheets(1)
        setup_settings_sheet(settings)
        calc = wb.Worksheets.Add(After=settings)
        layout = setup_calc_sheet(calc, xl, logo_png, header_png, footer_png)
        finalize_settings_sheet(settings, layout.text["max_chars"])
        fit = layout.fit
        info(f"열 너비 시도 기록 (ColumnWidth, PDF 페이지 수, A~Z mm): {list(fit.tried)}")
        info(
            f"열 너비 {fit.column_width} 선택 — 화면 {fit.screen_pt:.2f}pt / 100% PDF 실측 {fit.print_pt:.2f}pt"
            f" ({fit.print_pt / mm_to_pt(1):.2f}mm), A~Z {fit.span_mm:.2f}mm ≤ {PRINT_WIDTH_MM:.0f}mm,"
            f" 좌우 여백 {layout.margin_lr_mm:.2f}mm"
        )

        install_vba(wb, sources, layout.text)
        wb.SaveAs(str(save_to), XL_OPENXML_MACRO)
        # 매크로를 허용하지 않고 열어도 머리글이 보이도록, 저장 전에 한 번 반영해 둔다
        xl.Run(f"'{wb.Name}'!HeaderSync.UpdateHeaders")
        calc.Activate()
        calc.Range("A2").Select()
        wb.Save()
        wb.Close(False)
    finally:
        xl.EnableEvents = True
    return {"layout": layout}


def build(logo_src: Path | None, out: Path, assets: Path = ASSETS) -> dict:
    logo_png, logo_origin = resolve_logo(logo_src, assets)
    header_png = assets / HEADER_NAME  # 로고 + 문서명 (setup_calc_sheet 에서 합성)
    footer_png = assets / FOOTER_NAME  # 열 너비 실측 뒤 그 폭으로 만든다(setup_calc_sheet)
    sources = load_vba_sources()

    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp_out = out.with_name(out.stem + ".tmp.xlsm")
    result: dict = {"logo": str(logo_png), "logo_origin": logo_origin}

    with ExcelSession() as session:
        version = session.xl.Version
        result["excel_version"] = version
        result["vbom_before"] = read_access_vbom(version)
        info(f"AccessVBOM 시작 전 값 (Excel {version}): {describe_vbom(result['vbom_before'])}")
        if effective_access_vbom(result["vbom_before"]) != 1:
            print(VBOM_STOP_MESSAGE, file=sys.stderr)
            raise SystemExit(2)
        # COM 참조가 함수 지역 변수에만 남도록 따로 호출한다(끝나면 참조가 풀려 Quit 이 깔끔하게 된다)
        result.update(_build_workbook(session.xl, logo_png, header_png, footer_png, sources, tmp_out))

    shutil.move(str(tmp_out), str(out))
    info(f"저장 → {out}")

    result["vbom_after"] = read_access_vbom(result["excel_version"])
    before = effective_access_vbom(result["vbom_before"])
    after = effective_access_vbom(result["vbom_after"])
    changed = "변경 없음" if result["vbom_before"] == result["vbom_after"] else "변경됨(확인 필요)"
    info(f"AccessVBOM 종료 후 값: {describe_vbom(result['vbom_after'])}")
    print(f"AccessVBOM 시작 전 값 = {before}, 종료 후 값 = {after}, {changed}")
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="구조계산서 첨부용 엑셀 양식(.xlsm) 생성")
    p.add_argument(
        "--logo",
        type=Path,
        default=Path(r"C:\Users\KYB\Pictures\Saved Pictures\SNP FILE STATION.ico"),
        help="로고 원본(.ico/.png). 원본은 읽기만 하고 assets/logo.png 로 변환해서 씁니다. (기본값: %(default)s)",
    )
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"출력 .xlsm 경로. 기본값: {DEFAULT_OUT}")
    args = p.parse_args(argv)
    build(args.logo, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
