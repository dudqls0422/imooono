"""CLI: --make-template, --dry-run(네트워크 0), 종료코드 0/4/5."""
from __future__ import annotations

from tools.portal_frame_gen import cli
from tools.portal_frame_gen.template import read_template, write_template

from .conftest import FakeResp


def _template(tmp_path):
    f = tmp_path / "in.xlsx"
    write_template(str(f))
    return str(f)


class _NoNetClient:
    def __init__(self, *a, **k):
        raise AssertionError("dry-run 인데 네트워크 클라이언트가 생성됨")


def _fake_client_cls(get_map, put_map=None):
    class _C:
        def __init__(self, mapi_key, base_url=None, timeout=30):
            self.request_log = []
            self.puts = []
            self._get_map = get_map
            self._put_map = put_map or {}

        def get(self, path):
            self.request_log.append(("GET", path, 200))
            return self._get_map.get(path, {"message": ""})

        def put(self, path, body):
            self.puts.append((path, body))
            self.request_log.append(("PUT", path, 200))
            return self._put_map.get(path, FakeResp(200, {"ok": {}}))

        def delete(self, path):
            self.request_log.append(("DELETE", path, 200))
            return FakeResp(200, {})

        def verbs_used(self):
            return sorted({v for v, _p, _s in self.request_log})
    return _C


_FULL_GET = {
    "db/MATL": {"MATL": {"1": {"NAME": "SS275"}}},
    "db/SECT": {"SECT": {
        "10": {"SECT_NAME": "H-400x200x8x13"},
        "11": {"SECT_NAME": "H-350x175x7x11"},
        "12": {"SECT_NAME": "H-200x100x5.5x8"}}},
    "db/NODE": {"message": ""},
    "db/ELEM": {"message": ""},
    "db/CONS": {"message": ""},
}


def test_make_template(tmp_path):
    out = tmp_path / "tmpl.xlsx"
    assert cli.main(["--make-template", str(out)]) == 0
    assert out.exists()
    assert read_template(str(out)).span_m == 20.0


def test_dry_run_makes_no_network_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "PortalFrameClient", _NoNetClient)
    rc = cli.main(["--template", _template(tmp_path), "--dry-run"])
    assert rc == 0


def test_success_flow_get_and_put_only(tmp_path, monkeypatch):
    holder = {}
    cls = _fake_client_cls(_FULL_GET)

    def _factory(*a, **k):
        holder["c"] = cls(*a, **k)
        return holder["c"]

    monkeypatch.setattr(cli, "PortalFrameClient", _factory)
    rc = cli.main(["--template", _template(tmp_path), "--mapi-key", "k"])
    assert rc == 0
    assert holder["c"].verbs_used() == ["GET", "PUT"]
    assert [p for p, _b in holder["c"].puts][0] == "db/UNIT"


def test_exit_5_when_section_name_missing(tmp_path, monkeypatch):
    gm = dict(_FULL_GET)
    gm["db/SECT"] = {"SECT": {"10": {"SECT_NAME": "H-400x200x8x13"}}}
    monkeypatch.setattr(cli, "PortalFrameClient", _fake_client_cls(gm))
    rc = cli.main(["--template", _template(tmp_path), "--mapi-key", "k"])
    assert rc == 5


def test_exit_4_when_model_not_empty(tmp_path, monkeypatch):
    gm = dict(_FULL_GET)
    gm["db/NODE"] = {"NODE": {"1": {"X": 0, "Y": 0, "Z": 0}}}
    monkeypatch.setattr(cli, "PortalFrameClient", _fake_client_cls(gm))
    rc = cli.main(["--template", _template(tmp_path), "--mapi-key", "k"])
    assert rc == 4


def test_frame_mode_override_to_2d(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "PortalFrameClient", _NoNetClient)
    rc = cli.main(["--template", _template(tmp_path), "--dry-run",
                   "--frame-mode", "2D"])
    assert rc == 0
