"""형상 생성: 좌표·카운트·대칭·ID 채번."""
from __future__ import annotations

import pytest

from tools.portal_frame_gen.geometry import GeometryError, build_model
from tools.portal_frame_gen.model import (CONSTRAINT_FIXED, KIND_COLUMN,
                                          KIND_EAVE_STRUT)

from .conftest import make_params


def test_2d_example_coords_and_counts():
    m = build_model(make_params(frame_mode="2D"))
    coords = [(n.x, n.y, n.z) for n in m.nodes]
    assert coords == [(0.0, 0.0, 0.0), (0.0, 0.0, 6.0), (10.0, 0.0, 7.0),
                      (20.0, 0.0, 6.0), (20.0, 0.0, 0.0)]
    c = m.counts()
    assert c["nodes"] == 5 and c["elements"] == 4
    assert c["columns"] == 2 and c["rafters"] == 2 and c["eave_struts"] == 0
    assert c["supports"] == 2


def test_3d_example_counts():
    m = build_model(make_params(frame_mode="3D"))  # 20/6/1:10, 5 bays @ 6
    c = m.counts()
    assert m.meta["n_frames"] == 6
    assert c["nodes"] == 30
    assert c["elements"] == 34 and c["columns"] == 12 and c["rafters"] == 12
    assert c["eave_struts"] == 10
    assert c["supports"] == 12
    assert c["groups"] == 3


def test_3d_frame_y_positions():
    m = build_model(make_params(frame_mode="3D"))
    ys = sorted({round(n.y, 6) for n in m.nodes})
    assert ys == [0.0, 6.0, 12.0, 18.0, 24.0, 30.0]


def test_columns_are_vertical():
    m = build_model(make_params(frame_mode="3D"))
    by_id = {n.id: n for n in m.nodes}
    for e in m.elems_by_kind(KIND_COLUMN):
        assert abs(by_id[e.n1].x - by_id[e.n2].x) < 1e-9
        assert abs(by_id[e.n1].y - by_id[e.n2].y) < 1e-9


def test_one_ridge_node_per_frame():
    m = build_model(make_params(frame_mode="3D"))
    ridge = [n for n in m.nodes if abs(n.x - 10.0) < 1e-9]
    assert len(ridge) == m.meta["n_frames"]


def test_symmetry_left_right_bases():
    m = build_model(make_params(frame_mode="2D"))
    xs = sorted(n.x for n in m.nodes if abs(n.z) < 1e-9)
    assert xs == [0.0, 20.0]


def test_fixed_base_constraint():
    m = build_model(make_params(frame_mode="2D", base_fixity="fixed"))
    assert all(s.constraint == CONSTRAINT_FIXED for s in m.supports)


def test_eave_struts_link_adjacent_frames():
    m = build_model(make_params(frame_mode="3D"))
    struts = m.elems_by_kind(KIND_EAVE_STRUT)
    assert len(struts) == 10
    for e in struts:
        assert abs(e.n2 - e.n1) == 5  # 인접 프레임(노드 5개 간격)


def test_flat_roof_raises_geometry_error():
    with pytest.raises(GeometryError):
        build_model(make_params(pitch_rise=0.0))
