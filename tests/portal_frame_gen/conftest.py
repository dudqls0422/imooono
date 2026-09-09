"""포탈 프레임 생성기 테스트 공용 픽스처 (라이브 MIDAS 불필요)."""
from __future__ import annotations

import json

import pytest

from tools.portal_frame_gen.template import TemplateParams


def make_params(**over) -> TemplateParams:
    base = dict(
        span_m=20.0, eave_height_m=6.0, pitch_rise=1.0, pitch_run=10.0,
        roof_angle_deg=None, bay_count=5, bay_spacing_m=6.0, base_level_m=0.0,
        column_section="H-400x200x8x13", rafter_section="H-350x175x7x11",
        eave_strut_section="H-200x100x5.5x8", material_name="SS275",
        base_fixity="pinned", frame_mode="3D",
    )
    base.update(over)
    return TemplateParams(**base)


@pytest.fixture
def valid_params():
    return make_params()


# --------------------------------------------------------------------------
# 가짜 클라이언트
# --------------------------------------------------------------------------
class FakeResp:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code = status
        self._payload = payload
        self.text = text or (json.dumps(payload) if payload is not None else "")

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeClient:
    """get_map: {path: dict} / put_map: {path: FakeResp} (없으면 200 성공)."""

    def __init__(self, get_map=None, put_map=None, delete_map=None):
        self.get_map = get_map or {}
        self.put_map = put_map or {}
        self.delete_map = delete_map or {}
        self.puts = []       # [(path, body)]
        self.deletes = []    # [path]
        self.request_log = []

    def get(self, path):
        self.request_log.append(("GET", path, 200))
        return self.get_map.get(path, {"message": ""})

    def put(self, path, body):
        self.puts.append((path, body))
        self.request_log.append(("PUT", path, 200))
        return self.put_map.get(path, FakeResp(200, {path.split("/")[-1]: {}}))

    def delete(self, path):
        self.deletes.append(path)
        self.request_log.append(("DELETE", path, 200))
        return self.delete_map.get(path, FakeResp(200, {}))

    def verbs_used(self):
        return sorted({v for v, _p, _s in self.request_log})


@pytest.fixture
def matl_sect_get_map():
    """SS275 재료 + 3개 H형강 단면이 이미 정의된 빈 모델."""
    return {
        "db/MATL": {"MATL": {
            "1": {"TYPE": "STEEL", "NAME": "SS275",
                  "PARAM": [{"P_TYPE": 1, "STANDARD": "KS21(S)", "DB": "SS275"}]},
        }},
        "db/SECT": {"SECT": {
            "10": {"SECTTYPE": "DBUSER", "SECT_NAME": "H-400x200x8x13",
                   "SECT_BEFORE": {"SHAPE": "H", "SECT_I": {"DB_NAME": "KS21"}}},
            "11": {"SECTTYPE": "DBUSER", "SECT_NAME": "H-350x175x7x11",
                   "SECT_BEFORE": {"SHAPE": "H"}},
            "12": {"SECTTYPE": "DBUSER", "SECT_NAME": "H-200x100x5.5x8",
                   "SECT_BEFORE": {"SHAPE": "H"}},
        }},
        "db/NODE": {"message": ""},
        "db/ELEM": {"message": ""},
        "db/CONS": {"message": ""},
    }
