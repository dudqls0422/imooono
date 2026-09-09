"""각 체크: 정상(무검출) / 결함 주입(정확 검출). 최소 12개 체크 커버."""
from __future__ import annotations

from tools.model_qa.checks import load_all_checks
from tools.model_qa.checks.geometry import (g1_duplicate_nodes, g3_zero_length,
                                            g5_isolated_nodes, g6_dangling_nodes)
from tools.model_qa.checks.properties import (p1_material_missing,
                                              p2_section_missing,
                                              p3_abnormal_material)
from tools.model_qa.checks.boundary import (b1_no_supports, b2_global_rigid_body,
                                            b3_ghost_supports)
from tools.model_qa.checks.connectivity import c1_rigid_cycles, c3_dangling_load_refs
from tools.model_qa.checks.loads import l1_empty_load_cases, l3_case_not_in_combo
from tools.model_qa.checks.combos import k1_weak_combos, k3_combo_bad_ref

from .conftest import beam, make_ctx, node

load_all_checks()

FULL_CONS = {"1": {"ITEMS": [{"ID": 1, "CONSTRAINT": "1111110"}]}}


def test_g1_clean():
    ctx = make_ctx(nodes={"1": node(0, 0, 0), "2": node(1, 0, 0)})
    assert g1_duplicate_nodes(ctx) == []


def test_g1_duplicate():
    ctx = make_ctx(nodes={"1": node(0, 0, 0), "2": node(0.0002, 0, 0),
                          "3": node(5, 0, 0)})
    f = g1_duplicate_nodes(ctx)
    assert f and set(f[0].target_ids) == {1, 2} and f[0].severity == "오류"


def test_g3_zero_length():
    ctx = make_ctx(nodes={"1": node(0, 0, 0), "2": node(0.0003, 0, 0)},
                   elems={"10": beam(1, 2)})
    f = g3_zero_length(ctx)
    assert f and f[0].target_ids == [10]


def test_g3_ok():
    ctx = make_ctx(nodes={"1": node(0, 0, 0), "2": node(3, 0, 0)},
                   elems={"10": beam(1, 2)})
    assert g3_zero_length(ctx) == []


def test_g5_isolated():
    ctx = make_ctx(nodes={"1": node(0, 0, 0), "2": node(3, 0, 0), "9": node(9, 9, 9)},
                   elems={"1": beam(1, 2)})
    f = g5_isolated_nodes(ctx)
    assert f and f[0].target_ids == [9]


def test_g6_dangling():
    # 절점1 은 지점(FULL_CONS 키='1'), 절점2 는 차수2, 절점3 만 차수1·무지점 → dangling
    ctx = make_ctx(
        nodes={"1": node(0, 0, 0), "2": node(3, 0, 0), "3": node(6, 0, 0)},
        elems={"1": beam(1, 2), "2": beam(2, 3)}, cons=FULL_CONS)
    f = g6_dangling_nodes(ctx)
    assert f and set(f[0].target_ids) == {3}


def test_p1_material_missing():
    ctx = make_ctx(nodes={"1": node(0, 0, 0), "2": node(3, 0, 0)},
                   elems={"5": beam(1, 2, matl=0)}, matls={}, sects={"1": {}})
    f = p1_material_missing(ctx)
    assert f and f[0].target_ids == [5]


def test_p2_section_missing():
    ctx = make_ctx(nodes={"1": node(0, 0, 0), "2": node(3, 0, 0)},
                   elems={"5": beam(1, 2, sect=99)}, matls={"1": {}}, sects={"1": {}})
    f = p2_section_missing(ctx)
    assert f and f[0].target_ids == [5]


def test_p3_abnormal_e_and_density():
    ctx = make_ctx(
        elems={"1": beam(1, 2, matl=1)},
        matls={"1": {"PARAM": [{"ELAST": 0, "DEN": 0, "MASS": 0}]}},
        bodf={"1": {"LCNAME": "D", "FV": [0, 0, -1]}})
    f = p3_abnormal_material(ctx)
    assert f and 1 in f[0].target_ids


def test_p3_ok():
    ctx = make_ctx(elems={"1": beam(1, 2, matl=1)},
                   matls={"1": {"PARAM": [{"ELAST": 2e8, "DEN": 77, "MASS": 7.85}]}})
    assert p3_abnormal_material(ctx) == []


def test_b1_no_supports():
    ctx = make_ctx(nodes={"1": node(0, 0, 0)})
    f = b1_no_supports(ctx)
    assert f and f[0].severity == "오류"


def test_b2_free_dof():
    ctx = make_ctx(nodes={"1": node(0, 0, 0)},
                   cons={"1": {"ITEMS": [{"CONSTRAINT": "1110000"}]}})
    f = b2_global_rigid_body(ctx)
    assert f and "RZ" in f[0].description


def test_b2_ok_when_full():
    ctx = make_ctx(nodes={"1": node(0, 0, 0)}, cons=FULL_CONS)
    assert b2_global_rigid_body(ctx) == []


def test_b3_ghost_support():
    ctx = make_ctx(nodes={"1": node(0, 0, 0)},
                   cons={"1": {"ITEMS": [{"CONSTRAINT": "111000"}]},
                         "77": {"ITEMS": [{"CONSTRAINT": "111000"}]}})
    f = b3_ghost_supports(ctx)
    assert f and f[0].target_ids == [77]


def test_c1_multi_master():
    ctx = make_ctx(rigd={"1": {"ITEMS": [{"S_NODE": [3]}]},
                         "2": {"ITEMS": [{"S_NODE": [3]}]}})
    f = c1_rigid_cycles(ctx)
    assert any(3 in x.target_ids for x in f)


def test_c1_cycle():
    ctx = make_ctx(rigd={"1": {"ITEMS": [{"S_NODE": [2]}]},
                         "2": {"ITEMS": [{"S_NODE": [1]}]}})
    f = c1_rigid_cycles(ctx)
    assert any("순환" in x.description for x in f)


def test_c3_dangling_load_ref():
    ctx = make_ctx(nodes={"1": node(0, 0, 0)}, elems={"1": beam(1, 1)},
                   cnld={"99": {"ITEMS": [{"LCNAME": "D", "FZ": -10}]}},
                   bmld={"88": {"ITEMS": [{"LCNAME": "L"}]}})
    f = c3_dangling_load_refs(ctx)
    tgt = {t for x in f for t in x.target_ids}
    assert 99 in tgt and 88 in tgt


def test_l1_empty_case():
    ctx = make_ctx(stld={"1": {"NAME": "DL", "TYPE": "D"},
                         "2": {"NAME": "LL", "TYPE": "L"}},
                   cnld={"5": {"ITEMS": [{"LCNAME": "DL", "FZ": -1}]}})
    f = l1_empty_load_cases(ctx)
    assert f and f[0].target_ids == [2]


def test_l3_orphan_case():
    ctx = make_ctx(stld={"1": {"NAME": "DL", "TYPE": "D"},
                         "9": {"NAME": "SNOW", "TYPE": "S"}},
                   lcom={"LCOM-GEN": {"1": {"NAME": "C1",
                                            "vCOMB": [{"ANAL": "ST", "LCNAME": "DL",
                                                       "FACTOR": 1.4}]}}})
    f = l3_case_not_in_combo(ctx)
    assert f and f[0].target_ids == [9]


def test_k1_all_single():
    ctx = make_ctx(lcom={"LCOM-GEN": {
        "1": {"NAME": "A", "ACTIVE": "ACTIVE",
              "vCOMB": [{"ANAL": "ST", "LCNAME": "DL", "FACTOR": 1}]},
        "2": {"NAME": "B", "ACTIVE": "ACTIVE",
              "vCOMB": [{"ANAL": "ST", "LCNAME": "LL", "FACTOR": 1}]}}})
    f = k1_weak_combos(ctx)
    assert any("단일" in x.description for x in f)


def test_k3_bad_ref():
    ctx = make_ctx(stld={"1": {"NAME": "DL", "TYPE": "D"}},
                   lcom={"LCOM-GEN": {"1": {"NAME": "C1", "ACTIVE": "ACTIVE",
                                            "vCOMB": [{"ANAL": "ST",
                                                       "LCNAME": "GHOST",
                                                       "FACTOR": 1}]}}})
    f = k3_combo_bad_ref(ctx)
    assert f and f[0].severity == "오류" and "GHOST" in f[0].description


def test_whitelist_marks_finding():
    from tools.model_qa.config import ScanConfig
    from tools.model_qa.scan import _mark_whitelist
    c = ScanConfig(wl_element_groups=["DUMMY"])
    ctx = make_ctx(cfg=c,
                   nodes={"1": node(0, 0, 0), "2": node(0.0001, 0, 0)},
                   grup={"1": {"NAME": "DUMMY", "N_LIST": [1, 2], "E_LIST": []}})
    f = g1_duplicate_nodes(ctx)
    _mark_whitelist(ctx, f)
    assert f and f[0].whitelisted is True
