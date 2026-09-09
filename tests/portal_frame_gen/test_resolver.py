"""재료명·단면명 → 기존 id 해석."""
from __future__ import annotations

import pytest

from tools.portal_frame_gen.resolver import NamesNotFound, resolve_ids

from .conftest import FakeClient

_SECTS = ["H-400x200x8x13", "H-350x175x7x11", "H-200x100x5.5x8"]


def test_resolve_ok(matl_sect_get_map):
    c = FakeClient(get_map=matl_sect_get_map)
    r = resolve_ids(c, "SS275", _SECTS)
    assert r.material_id == 1
    assert r.section_ids == {"H-400x200x8x13": 10, "H-350x175x7x11": 11,
                             "H-200x100x5.5x8": 12}


def test_resolve_material_via_db_fallback():
    gm = {
        "db/MATL": {"MATL": {"7": {"NAME": "내재료", "TYPE": "STEEL",
                                   "PARAM": [{"DB": "SS275"}]}}},
        "db/SECT": {"SECT": {"3": {"SECT_NAME": "H-A"}}},
    }
    r = resolve_ids(FakeClient(get_map=gm), "SS275", ["H-A"])
    assert r.material_id == 7


def test_resolve_section_via_sect_i_fallback():
    gm = {
        "db/MATL": {"MATL": {"1": {"NAME": "SS275"}}},
        "db/SECT": {"SECT": {"9": {"SECT_NAME": "별칭",
                                   "SECT_BEFORE": {"SECT_I": {"SECT_NAME": "H-A"}}}}},
    }
    r = resolve_ids(FakeClient(get_map=gm), "SS275", ["H-A"])
    assert r.section_ids["H-A"] == 9


def test_resolve_missing_section(matl_sect_get_map):
    c = FakeClient(get_map=matl_sect_get_map)
    with pytest.raises(NamesNotFound) as ei:
        resolve_ids(c, "SS275", ["H-400x200x8x13", "H-999"])
    assert ei.value.missing_sections == ["H-999"]
    assert not ei.value.missing_materials


def test_resolve_missing_material(matl_sect_get_map):
    c = FakeClient(get_map=matl_sect_get_map)
    with pytest.raises(NamesNotFound) as ei:
        resolve_ids(c, "SM355", _SECTS)
    assert ei.value.missing_materials == ["SM355"]


def test_resolve_empty_collection_is_not_defined():
    gm = {"db/MATL": {"message": ""}, "db/SECT": {"message": ""}}
    with pytest.raises(NamesNotFound):
        resolve_ids(FakeClient(get_map=gm), "SS275", ["H-A"])
