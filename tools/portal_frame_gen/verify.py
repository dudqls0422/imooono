"""생성 직후 읽기대조: 라이브 GET 결과 == 계산 모델.

GET db/NODE(좌표 ±1e-6 m), db/ELEM(연결·MATL·SECT), db/CONS(구속 문자열),
카운트 일치를 확인한다. 불일치 목록을 반환하며 빈 리스트면 통과.
"""
from __future__ import annotations

from typing import Dict, List

from .model import PortalFrameModel

_COORD_TOL = 1e-6


def _coll(body, key) -> Dict:
    if not isinstance(body, dict):
        return {}
    if "message" in body and not body.get(key):
        return {}
    inner = body.get(key)
    return inner if isinstance(inner, dict) else {}


def verify_model(client, model: PortalFrameModel, resolved,
                 log=print) -> List[str]:
    problems: List[str] = []
    nodes = _coll(client.get("db/NODE"), "NODE")
    elems = _coll(client.get("db/ELEM"), "ELEM")
    cons = _coll(client.get("db/CONS"), "CONS")

    if len(nodes) != len(model.nodes):
        problems.append(f"절점 수 불일치: 라이브 {len(nodes)} vs 모델 {len(model.nodes)}")
    if len(elems) != len(model.elements):
        problems.append(f"요소 수 불일치: 라이브 {len(elems)} vs 모델 {len(model.elements)}")

    for n in model.nodes:
        row = nodes.get(str(n.id))
        if row is None:
            problems.append(f"절점 {n.id} 없음")
            continue
        for axis, want in (("X", n.x), ("Y", n.y), ("Z", n.z)):
            got = _f(row.get(axis))
            if got is None or abs(got - want) > _COORD_TOL:
                problems.append(
                    f"절점 {n.id}.{axis} 불일치: 라이브 {got} vs 모델 {want}")

    for e in model.elements:
        row = elems.get(str(e.id))
        if row is None:
            problems.append(f"요소 {e.id} 없음")
            continue
        got_nodes = [int(x) for x in (row.get("NODE") or [])
                     if x not in (0, "0", None)]
        if got_nodes[:2] != [e.n1, e.n2]:
            problems.append(
                f"요소 {e.id} 연결 불일치: 라이브 {got_nodes} vs 모델 [{e.n1}, {e.n2}]")
        if _i(row.get("MATL")) != resolved.material_id:
            problems.append(
                f"요소 {e.id} MATL 불일치: 라이브 {row.get('MATL')} vs "
                f"모델 {resolved.material_id}")
        want_sect = resolved.section_ids.get(e.section_name)
        if _i(row.get("SECT")) != want_sect:
            problems.append(
                f"요소 {e.id} SECT 불일치: 라이브 {row.get('SECT')} vs 모델 {want_sect}")

    for s in model.supports:
        row = cons.get(str(s.node_id))
        if row is None:
            problems.append(f"지점 노드 {s.node_id} 없음")
            continue
        items = row.get("ITEMS") or []
        got = str(items[0].get("CONSTRAINT", "")) if items else ""
        if got[:7] != s.constraint:
            problems.append(
                f"지점 {s.node_id} 구속 불일치: 라이브 {got!r} vs 모델 {s.constraint!r}")

    if problems:
        log(f"[verify] 불일치 {len(problems)}건:")
        for p in problems:
            log(f"  - {p}")
    else:
        log("[verify] 라이브 모델이 계산 모델과 일치 (좌표·연결·재료·단면·지점).")
    return problems


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _i(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
