"""writer: PUT 순서·바디, 빈 모델 가드, 부분 실패."""
from __future__ import annotations

import pytest

from tools.portal_frame_gen.geometry import build_model
from tools.portal_frame_gen.resolver import ResolvedIds
from tools.portal_frame_gen.writer import (UNIT_BODY, LiveWriteUnsupported,
                                           ModelNotEmpty, WriteFailed,
                                           empty_model_guard, put_unit,
                                           write_model)

from .conftest import FakeClient, FakeResp, make_params

_RESOLVED = ResolvedIds(material_id=1, section_ids={
    "H-400x200x8x13": 10, "H-350x175x7x11": 11, "H-200x100x5.5x8": 12})


def _quiet(*_a, **_k):
    pass


def test_put_unit_success():
    c = FakeClient()
    put_unit(c, log=_quiet)
    assert c.puts == [("db/UNIT", UNIT_BODY)]


def test_put_unit_unsupported_raises():
    c = FakeClient(put_map={"db/UNIT": FakeResp(405, text="Method Not Allowed")})
    with pytest.raises(LiveWriteUnsupported):
        put_unit(c, log=_quiet)


def test_empty_guard_blocks_when_nodes_exist():
    c = FakeClient(get_map={"db/NODE": {"NODE": {"1": {"X": 0}}},
                            "db/ELEM": {"message": ""}})
    with pytest.raises(ModelNotEmpty):
        empty_model_guard(c, force=False, log=_quiet)


def test_empty_guard_force_bypasses():
    c = FakeClient(get_map={"db/NODE": {"NODE": {"1": {"X": 0}}},
                            "db/ELEM": {"message": ""}})
    empty_model_guard(c, force=True, log=_quiet)  # 예외 없음


def test_empty_guard_ok_when_empty():
    c = FakeClient(get_map={"db/NODE": {"message": ""},
                            "db/ELEM": {"message": ""}})
    empty_model_guard(c, force=False, log=_quiet)


def test_write_model_order_and_bodies():
    m = build_model(make_params(frame_mode="2D"))
    c = FakeClient()
    write_model(c, m, _RESOLVED, no_groups=False, log=_quiet)
    assert [p for p, _b in c.puts] == ["db/NODE", "db/ELEM", "db/CONS", "db/GRUP"]

    nbody = dict(c.puts[0][1])
    assert set(nbody["Assign"].keys()) == {"1", "2", "3", "4", "5"}
    assert nbody["Assign"]["3"] == {"X": 10.0, "Y": 0.0, "Z": 7.0}

    ebody = c.puts[1][1]
    e1 = ebody["Assign"]["1"]
    assert e1["TYPE"] == "BEAM" and e1["MATL"] == 1 and e1["SECT"] == 10
    assert e1["NODE"] == [1, 2]

    cbody = c.puts[2][1]
    assert cbody["Assign"]["1"]["ITEMS"][0]["CONSTRAINT"] == "1110000"

    gbody = c.puts[3][1]
    assert {v["NAME"] for v in gbody["Assign"].values()} == {"COLUMN", "RAFTER"}


def test_write_model_no_groups():
    m = build_model(make_params(frame_mode="2D"))
    c = FakeClient()
    write_model(c, m, _RESOLVED, no_groups=True, log=_quiet)
    assert [p for p, _b in c.puts] == ["db/NODE", "db/ELEM", "db/CONS"]


def test_write_model_partial_failure_reports_done():
    m = build_model(make_params(frame_mode="2D"))
    c = FakeClient(put_map={"db/ELEM": FakeResp(
        500, {"error": {"code": "E1", "message": "bad ref"}})})
    with pytest.raises(WriteFailed) as ei:
        write_model(c, m, _RESOLVED, log=_quiet)
    assert ei.value.step == "ELEM"
    assert ei.value.done == ["NODE"]


def test_write_model_200_with_message_is_failure():
    """MIDAS 가 200 + {"message":"Invalid..."} 로 실패를 줄 수 있음 — 삼키면 안 됨."""
    m = build_model(make_params(frame_mode="2D"))
    c = FakeClient(put_map={"db/NODE": FakeResp(
        200, {"message": "Invalid node data"})})
    with pytest.raises(WriteFailed) as ei:
        write_model(c, m, _RESOLVED, log=_quiet)
    assert ei.value.step == "NODE" and ei.value.done == []


def test_write_model_echoed_collection_key_is_success():
    m = build_model(make_params(frame_mode="2D"))
    c = FakeClient(put_map={
        "db/NODE": FakeResp(200, {"NODE": {"1": {"X": 0}}}),
        "db/ELEM": FakeResp(200, {"ELEM": {}}),
        "db/CONS": FakeResp(200, {"CONS": {}}),
        "db/GRUP": FakeResp(200, {"GRUP": {}}),
    })
    out = write_model(c, m, _RESOLVED, log=_quiet)
    assert out["done"] == ["NODE", "ELEM", "CONS", "GRUP"]
