"""공용 픽스처 헬퍼: 합성 ScanContext 생성."""
from __future__ import annotations

import pytest

from tools.model_qa.config import ScanConfig
from tools.model_qa.scan import ScanContext, _build_inactive_elems, _build_whitelist


def node(x, y, z):
    return {"X": float(x), "Y": float(y), "Z": float(z)}


def beam(n1, n2, matl=1, sect=1, typ="BEAM"):
    return {"TYPE": typ, "MATL": matl, "SECT": sect, "NODE": [n1, n2], "ANGLE": 0}


def plate(ns, matl=1, sect=1, typ="PLATE"):
    return {"TYPE": typ, "MATL": matl, "SECT": sect, "NODE": list(ns), "ANGLE": 0}


def make_ctx(cfg=None, **collections):
    ctx = ScanContext(cfg=cfg or ScanConfig())
    ctx.unit_raw = {"FORCE": "KN", "DIST": "M", "HEAT": "KCAL", "TEMPER": "C"}
    for k, v in collections.items():
        setattr(ctx, k, v)
    _build_whitelist(ctx)
    _build_inactive_elems(ctx)
    return ctx


@pytest.fixture
def cfg():
    return ScanConfig()
