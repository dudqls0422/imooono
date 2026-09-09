"""템플릿 파라미터 → 계산 모델(노드·요소·지점·그룹).

부재 중심선 기준. 좌표계 X=스팬방향, Y=길이방향, Z=수직 상향.
ID 채번(빈 모델, 명시 지정):
- 노드: 프레임순(y 오름차순), 프레임 내 좌베이스→좌처마→용마루→우처마→우베이스
  = 1..5·n_frames.
- 요소: 전 기둥 → 전 rafter → 전 이브스트럿.
- 지점: 프레임별 좌·우 베이스 노드.
"""
from __future__ import annotations

import math
from typing import List

from .model import (CONSTRAINT_FIXED, CONSTRAINT_PINNED, KIND_COLUMN,
                    KIND_EAVE_STRUT, KIND_RAFTER, RAFTER_BETA_ANGLE, Element,
                    Group, Node, PortalFrameModel, Support)


class GeometryError(ValueError):
    """형상 파라미터가 물리적으로 성립하지 않음."""


def _slope(params) -> float:
    """지붕 슬로프비(rise/run). roof_angle_deg 가 있으면 그것을 우선."""
    if params.roof_angle_deg is not None:
        return math.tan(math.radians(params.roof_angle_deg))
    return params.pitch_rise / params.pitch_run


def frame_y_positions(params) -> List[float]:
    if params.frame_mode == "2D":
        return [0.0]
    n_frames = params.bay_count + 1
    return [i * params.bay_spacing_m for i in range(n_frames)]


def build_model(params) -> PortalFrameModel:
    span = params.span_m
    base = params.base_level_m
    eave_z = base + params.eave_height_m
    slope = _slope(params)
    ridge_z = base + params.eave_height_m + (span / 2.0) * slope
    if ridge_z <= eave_z + 1e-9:
        raise GeometryError(
            f"용마루 높이({ridge_z:.4f} m)가 처마 높이({eave_z:.4f} m) 이하 — "
            "지붕 슬로프가 0 이하이거나 파라미터 오류.")

    ys = frame_y_positions(params)
    n_frames = len(ys)
    constraint = (CONSTRAINT_FIXED if params.base_fixity == "fixed"
                  else CONSTRAINT_PINNED)

    model = PortalFrameModel()
    model.meta = {
        "span_m": span, "eave_height_m": params.eave_height_m,
        "base_level_m": base, "slope": slope, "ridge_height_m": ridge_z,
        "roof_angle_deg": math.degrees(math.atan(slope)),
        "frame_mode": params.frame_mode, "n_frames": n_frames,
        "bay_count": params.bay_count if params.frame_mode == "3D" else 0,
        "bay_spacing_m": params.bay_spacing_m if params.frame_mode == "3D" else 0.0,
        "material_name": params.material_name,
        "column_section": params.column_section,
        "rafter_section": params.rafter_section,
        "eave_strut_section": params.eave_strut_section,
    }

    # --- 노드: 프레임순, 프레임 내 5개 --------------------------------
    for f, y in enumerate(ys):
        b = 5 * f
        model.nodes.append(Node(b + 1, 0.0, y, base))            # 좌베이스
        model.nodes.append(Node(b + 2, 0.0, y, eave_z))          # 좌처마
        model.nodes.append(Node(b + 3, span / 2.0, y, ridge_z))  # 용마루
        model.nodes.append(Node(b + 4, span, y, eave_z))         # 우처마
        model.nodes.append(Node(b + 5, span, y, base))           # 우베이스

    # --- 요소: 전 기둥 → 전 rafter → 전 이브스트럿 -------------------
    eid = 0
    for f in range(n_frames):
        b = 5 * f
        eid += 1
        model.elements.append(Element(eid, KIND_COLUMN, b + 1, b + 2,
                                      params.column_section, 0.0))
        eid += 1
        model.elements.append(Element(eid, KIND_COLUMN, b + 5, b + 4,
                                      params.column_section, 0.0))
    for f in range(n_frames):
        b = 5 * f
        eid += 1
        model.elements.append(Element(eid, KIND_RAFTER, b + 2, b + 3,
                                      params.rafter_section, RAFTER_BETA_ANGLE))
        eid += 1
        model.elements.append(Element(eid, KIND_RAFTER, b + 4, b + 3,
                                      params.rafter_section, RAFTER_BETA_ANGLE))
    if params.frame_mode == "3D":
        # 좌처마 라인 → 우처마 라인, 각 라인 인접 프레임 연결
        for local in (2, 4):  # 좌처마=+2, 우처마=+4
            for f in range(n_frames - 1):
                eid += 1
                model.elements.append(Element(
                    eid, KIND_EAVE_STRUT, 5 * f + local, 5 * (f + 1) + local,
                    params.eave_strut_section, 0.0))

    # --- 지점: 프레임별 좌·우 베이스 --------------------------------
    for f in range(n_frames):
        b = 5 * f
        model.supports.append(Support(b + 1, constraint))
        model.supports.append(Support(b + 5, constraint))

    # --- 그룹 ------------------------------------------------------
    model.groups.append(Group("COLUMN",
                              [e.id for e in model.elems_by_kind(KIND_COLUMN)]))
    model.groups.append(Group("RAFTER",
                              [e.id for e in model.elems_by_kind(KIND_RAFTER)]))
    if params.frame_mode == "3D":
        model.groups.append(Group(
            "EAVE_STRUT",
            [e.id for e in model.elems_by_kind(KIND_EAVE_STRUT)]))
    return model
