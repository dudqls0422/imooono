"""이식 함수 + build_model: 스팬 파싱, 카운트 공식, 입력 검증."""
from __future__ import annotations

import itertools

import pytest

from tools.warehouse_frame_gen.geometry import (GeometryError, build_model,
                                                parse_span_expression)

from .conftest import make_params


# --- parse_span_expression (원본 이식 함수) --------------------------------
def test_parse_span_expression_ok():
    assert parse_span_expression("2, 4@4, 2") == [2.0, 4.0, 4.0, 4.0, 4.0, 2.0]
    assert parse_span_expression("5") == [5.0]
    assert parse_span_expression(" 3 , 3 ") == [3.0, 3.0]


@pytest.mark.parametrize("bad", ["4@0", "4@", "@4", "@", "", "   ", "-3",
                                 "3, -1", "abc", "4@x"])
def test_parse_span_expression_errors(bad):
    with pytest.raises(ValueError):
        parse_span_expression(bad)


# --- 카운트 공식: 옵션 매트릭스 전체에서 분해합 == 실제 dict 길이 --------
_MATRIX = list(itertools.product(
    [True, False], [True, False], [True, False], [1, 2], [0, 2]))


@pytest.mark.parametrize("sb,st,ur,sd,npur", _MATRIX)
def test_count_matrix_derive_equals_actual(sb, st, ur, sd, npur):
    p = make_params(skip_bottom_beam=sb, skip_top_beam=st, use_ridge=ur,
                    rafter_subdiv=sd, num_purlins=npur)
    m = build_model(p)
    c = m.counts
    breakdown = (c["x_beams"] + c["y_beams"] + c["columns"] + c["eave_x_beams"]
                 + c["ridge_x_beams"] + c["rafters"] + c["purlin_beams"])
    assert c["nodes"] == m.node_count()
    assert c["elements"] == m.elem_count() == breakdown


def test_count_baseline_no_skip_no_ridge():
    # 기준식: 절점 nx*ny*nz, X보 (nx-1)*ny*nz, Y보 nx*(ny-1)*nz, 기둥 (nz-1)*nx*ny
    p = make_params(skip_bottom_beam=False, skip_top_beam=False,
                    use_ridge=False, nz=3)
    nx = len(p["x_spans"]) + 1  # 7
    ny, nz = p["ny"], p["nz"]    # 4, 3
    m = build_model(p)
    assert m.node_count() == nx * ny * nz
    c = m.counts
    assert c["x_beams"] == (nx - 1) * ny * nz
    assert c["y_beams"] == nx * (ny - 1) * nz
    assert c["columns"] == (nz - 1) * nx * ny
    assert c["eave_x_beams"] == 0 and c["rafters"] == 0


def test_skip_bottom_removes_both_x_and_y_at_k0():
    full = build_model(make_params(skip_bottom_beam=False, skip_top_beam=False,
                                   use_ridge=False))
    skip = build_model(make_params(skip_bottom_beam=True, skip_top_beam=False,
                                   use_ridge=False))
    nx = len(make_params()["x_spans"]) + 1
    ny = 4
    # k=0 층의 X보 (nx-1)*ny 개 + Y보 nx*(ny-1) 개가 빠져야 함
    removed = (nx - 1) * ny + nx * (ny - 1)
    assert full.elem_count() - skip.elem_count() == removed


# --- 입력 검증: 거부 ---------------------------------------------------
@pytest.mark.parametrize("over", [
    {"ny": 0}, {"nz": 0}, {"dy": 0}, {"dz": -1},
    {"use_ridge": True, "rise": 0}, {"rafter_subdiv": 0},
    {"num_purlins": -1}, {"node_start": 0}, {"elem_start": 0},
    {"matl": 0}, {"sect": -2}, {"x_spans": []},
])
def test_validate_reject(over):
    with pytest.raises(GeometryError):
        build_model(make_params(**over))


# --- 입력 검증: 경고(거부 아님) -------------------------------------
def test_warn_no_columns():
    m = build_model(make_params(nz=1, use_ridge=False))
    assert any("기둥" in w for w in m.meta["warnings"])


def test_warn_weak_out_of_plane():
    m = build_model(make_params(ny=1))
    assert any("면외" in w for w in m.meta["warnings"])


def test_warn_lateral_quasi_mechanism():
    m = build_model(make_params(skip_bottom_beam=True, skip_top_beam=True, nz=2))
    assert any("준기구" in w for w in m.meta["warnings"])


def test_warn_unrealistic_rise():
    m = build_model(make_params(rise=999.0))
    assert any("물매" in w for w in m.meta["warnings"])
