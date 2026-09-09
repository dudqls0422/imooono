"""Excel 템플릿 읽기 + 검증 + 빈 양식 생성(``--make-template``).

레이아웃: 단일 시트, 1행 = 헤더명, 2행 = 예시(또는 사용자 입력) 1행,
3행 이후 `#` 로 시작하면 주석으로 무시. 리더는 첫 데이터 행(2행)을 읽는다.

단면·재료명은 **MIDAS DB(현재 모델)에 이미 정의돼 있어야 한다** — 이 도구는
만들지 않고 이름으로 기존 id 를 찾는다(``resolver``).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment

HEADERS = [
    "span_m", "eave_height_m", "pitch_rise", "pitch_run", "roof_angle_deg",
    "bay_count", "bay_spacing_m", "base_level_m",
    "column_section", "rafter_section", "eave_strut_section",
    "material_name", "base_fixity", "frame_mode",
]

_EXAMPLE_ROW = [
    20.0, 6.0, 1.0, 10.0, None,
    5, 6.0, 0.0,
    "H-400x200x8x13", "H-350x175x7x11", "H-200x100x5.5x8",
    "SS275", "pinned", "3D",
]

_NOTE = ("# 단면명(column/rafter/eave_strut)과 material_name 은 MIDAS 현재 모델에 "
         "이미 정의돼 있어야 함. roof_angle_deg 를 채우면 pitch_rise/run 대신 사용. "
         "frame_mode=2D 면 bay_* 무시. base_fixity: pinned|fixed.")

_FIXITY = {"pinned", "fixed"}
_MODE = {"2D", "3D"}

# 지붕 경사각(도) 경고/거부 임계
_ANGLE_WARN = 30.0
_ANGLE_REJECT = 45.0


class TemplateError(ValueError):
    """템플릿 파싱/검증 실패 (거부)."""


@dataclass
class TemplateParams:
    span_m: float
    eave_height_m: float
    pitch_rise: float
    pitch_run: float
    roof_angle_deg: Optional[float]
    bay_count: int
    bay_spacing_m: float
    base_level_m: float
    column_section: str
    rafter_section: str
    eave_strut_section: str
    material_name: str
    base_fixity: str
    frame_mode: str
    warnings: List[str] = field(default_factory=list)

    def roof_angle(self) -> float:
        if self.roof_angle_deg is not None:
            return self.roof_angle_deg
        return math.degrees(math.atan2(self.pitch_rise, self.pitch_run))


# --------------------------------------------------------------------------
# 읽기
# --------------------------------------------------------------------------
def _to_float(v, name):
    if v is None or v == "":
        raise TemplateError(f"'{name}' 값이 비어 있음")
    try:
        return float(v)
    except (TypeError, ValueError):
        raise TemplateError(f"'{name}' 값이 숫자가 아님: {v!r}")


def _opt_float(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_str(v, name):
    s = "" if v is None else str(v).strip()
    if not s:
        raise TemplateError(f"'{name}' 값이 비어 있음 (단면/재료명은 필수)")
    return s


def _parse_bay_spacing(raw, bay_count):
    """스칼라 또는 콤마 리스트. 리스트면 길이==bay_count 이고 균일해야 함."""
    if isinstance(raw, str) and "," in raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if len(parts) != bay_count:
            raise TemplateError(
                f"bay_spacing_m 리스트 길이({len(parts)})가 bay_count({bay_count})와 다름")
        try:
            vals = [float(p) for p in parts]
        except ValueError:
            raise TemplateError(f"bay_spacing_m 리스트에 숫자가 아닌 값: {raw!r}")
        if max(vals) - min(vals) > 1e-9:
            raise TemplateError("가변 베이 간격은 미지원 — 균일 간격(스칼라)만 허용")
        return vals[0]
    return _to_float(raw, "bay_spacing_m")


def read_template(path: str) -> TemplateParams:
    wb = load_workbook(path, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        raise TemplateError("템플릿에 데이터 행이 없음 (헤더 + 최소 1행 필요)")
    header = [str(c).strip() if c is not None else "" for c in rows[0]]
    idx = {h: i for i, h in enumerate(header)}
    missing_cols = [h for h in HEADERS if h not in idx]
    if missing_cols:
        raise TemplateError(f"템플릿 헤더 누락: {', '.join(missing_cols)}")

    data_row = None
    for r in rows[1:]:
        first = r[0] if r else None
        if first is None or str(first).strip() == "":
            continue
        if str(first).strip().startswith("#"):
            continue
        data_row = r
        break
    if data_row is None:
        raise TemplateError("템플릿에 유효한 데이터 행이 없음")

    def cell(name):
        i = idx[name]
        return data_row[i] if i < len(data_row) else None

    bay_count = _to_float(cell("bay_count"), "bay_count")
    if bay_count != int(bay_count):
        raise TemplateError(f"bay_count 는 정수여야 함: {bay_count}")
    bay_count = int(bay_count)

    params = TemplateParams(
        span_m=_to_float(cell("span_m"), "span_m"),
        eave_height_m=_to_float(cell("eave_height_m"), "eave_height_m"),
        pitch_rise=_to_float(cell("pitch_rise"), "pitch_rise"),
        pitch_run=_to_float(cell("pitch_run"), "pitch_run"),
        roof_angle_deg=_opt_float(cell("roof_angle_deg")),
        bay_count=bay_count,
        bay_spacing_m=_parse_bay_spacing(cell("bay_spacing_m"), bay_count),
        base_level_m=_to_float(cell("base_level_m"), "base_level_m"),
        column_section=_to_str(cell("column_section"), "column_section"),
        rafter_section=_to_str(cell("rafter_section"), "rafter_section"),
        eave_strut_section=_to_str(cell("eave_strut_section"), "eave_strut_section"),
        material_name=_to_str(cell("material_name"), "material_name"),
        base_fixity=str(cell("base_fixity") or "").strip().lower(),
        frame_mode=str(cell("frame_mode") or "").strip().upper(),
    )
    validate(params)
    return params


# --------------------------------------------------------------------------
# 검증
# --------------------------------------------------------------------------
def validate(p: TemplateParams) -> TemplateParams:
    if p.span_m <= 0:
        raise TemplateError(f"span_m 은 0 보다 커야 함: {p.span_m}")
    if p.eave_height_m <= 0:
        raise TemplateError(f"eave_height_m 은 0 보다 커야 함: {p.eave_height_m}")
    if p.bay_count < 1:
        raise TemplateError(f"bay_count 는 1 이상이어야 함: {p.bay_count}")
    if p.bay_spacing_m <= 0:
        raise TemplateError(f"bay_spacing_m 은 0 보다 커야 함: {p.bay_spacing_m}")
    if p.base_fixity not in _FIXITY:
        raise TemplateError(f"base_fixity 는 pinned|fixed: {p.base_fixity!r}")
    if p.frame_mode not in _MODE:
        raise TemplateError(f"frame_mode 는 2D|3D: {p.frame_mode!r}")

    if p.roof_angle_deg is None:
        if p.pitch_rise <= 0 or p.pitch_run <= 0:
            raise TemplateError(
                f"pitch_rise/pitch_run 은 0 보다 커야 함: {p.pitch_rise}/{p.pitch_run}")
    else:
        if p.roof_angle_deg <= 0:
            raise TemplateError(f"roof_angle_deg 는 0 보다 커야 함: {p.roof_angle_deg}")

    angle = p.roof_angle()
    if angle >= _ANGLE_REJECT:
        raise TemplateError(
            f"지붕 경사각 {angle:.1f}° — {_ANGLE_REJECT:.0f}° 이상은 포탈 프레임 범위 밖(거부)")
    if angle >= _ANGLE_WARN:
        p.warnings.append(
            f"지붕 경사각 {angle:.1f}° — {_ANGLE_WARN:.0f}~{_ANGLE_REJECT:.0f}° 는 이례적(경고)")

    slope = (math.tan(math.radians(p.roof_angle_deg))
             if p.roof_angle_deg is not None else p.pitch_rise / p.pitch_run)
    ridge = p.base_level_m + p.eave_height_m + (p.span_m / 2.0) * slope
    eave = p.base_level_m + p.eave_height_m
    if ridge <= eave + 1e-9:
        raise TemplateError(
            f"용마루({ridge:.4f} m) ≤ 처마({eave:.4f} m) — 슬로프가 0 이하")
    return p


# --------------------------------------------------------------------------
# 빈 양식 생성
# --------------------------------------------------------------------------
def write_template(path: str) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "portal_frame"
    ws.append(HEADERS)
    ws.append(_EXAMPLE_ROW)
    ws.append([_NOTE])
    for name in ("column_section", "rafter_section", "eave_strut_section",
                 "material_name"):
        col = HEADERS.index(name) + 1
        ws.cell(row=1, column=col).comment = Comment(
            "MIDAS 현재 모델에 이미 정의된 이름이어야 함", "portal_frame_gen")
    for i, _h in enumerate(HEADERS, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = 16
    wb.save(path)
