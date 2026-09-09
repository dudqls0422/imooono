"""정찰용 GET 전용 프로브 (재사용).

두 가지 용도:
1. midas-api 스킬 catalog(``endpoint_catalog.json``)에서 후보 엔드포인트의 실존/verb/스키마 덤프.
2. ``--live <MAPI-Key>`` 로 실제 MIDAS 에 GET 만 날려 응답 형태 확인 (mutating verb 없음).

사용::

    python -m tools.model_qa.recon_probe --catalog <path/to/endpoint_catalog.json>
    python -m tools.model_qa.recon_probe --live <MAPI-KEY> [--base-url ...]
"""
from __future__ import annotations

import argparse
import json
import sys

DEFAULT_BASE_URL = "https://moa-engineers.midasit.com:443/gen"

PROBE_KEYS = [
    "UNIT", "NODE", "ELEM", "MATL", "SECT", "THIK", "CONS", "NSPR", "GSPR",
    "GSTP", "SSPS", "SDSP", "RIGD", "ELNK", "STOR", "DRLS", "STLD", "CNLD",
    "BMLD", "PRES", "BODF", "GRUP", "BNGR", "LDGR", "NMAS", "LTOM", "STAG",
    "SPLC", "SWIND", "SSEIS", "SPFC", "POSL",
    "LCOM-GEN", "LCOM-CONC", "LCOM-STEEL", "LCOM-SRC", "LCOM-STLCOMP", "LCOM-SEISMIC",
]


def probe_catalog(path):
    data = json.load(open(path, encoding="utf-8"))
    by_uri = {}
    for e in data:
        u = e.get("input_uri")
        if u:
            by_uri.setdefault(u, []).append(e)
    for k in PROBE_KEYS:
        hits = by_uri.get(f"db/{k}", [])
        if not hits:
            print(f"db/{k:14} : *** catalog 에 없음 ***")
            continue
        for e in hits:
            props = []
            sch = e.get("schema") or {}
            if isinstance(sch, dict):
                for v in sch.values():
                    if isinstance(v, dict) and "properties" in v:
                        props = list(v["properties"])[:20]
                        break
            print(f"db/{k:14} : {e.get('name')!r} methods={e.get('active_methods')} props={props}")


def probe_live(key, base_url):
    import requests
    h = {"MAPI-Key": key, "Content-Type": "application/json"}
    for k in PROBE_KEYS:
        try:
            r = requests.get(f"{base_url.rstrip('/')}/db/{k}", headers=h, timeout=30)
            body = r.text[:400]
            try:
                j = r.json()
                body = f"keys={list(j) if isinstance(j, dict) else type(j).__name__}"
            except ValueError:
                pass
            print(f"GET db/{k:14} -> {r.status_code}  {body}")
        except Exception as e:
            print(f"GET db/{k:14} -> 예외 {type(e).__name__}: {e}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m tools.model_qa.recon_probe")
    p.add_argument("--catalog", help="endpoint_catalog.json 경로")
    p.add_argument("--live", help="MAPI-Key (실제 GET 프로브)")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    a = p.parse_args(argv)
    if a.catalog:
        probe_catalog(a.catalog)
    elif a.live:
        probe_live(a.live, a.base_url)
    else:
        p.print_usage()
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
