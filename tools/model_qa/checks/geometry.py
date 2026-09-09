"""지오메트리 점검 G1~G7."""
from __future__ import annotations

import math
from itertools import combinations

from . import Finding, SEVERITY_ERROR, SEVERITY_WARN, SEVERITY_INFO, register


def _line_elems(ctx):
    out = {}
    for eid, e in ctx.elems.items():
        ns = ctx.elem_nodes(e)
        if len(ns) == 2:
            out[eid] = ns
    return out


def _dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


@register("G1", "중복 절점")
def g1_duplicate_nodes(ctx):
    tol = max(ctx.cfg.tol_merge_m, 1e-9)
    buckets = {}
    for nid, n in ctx.nodes.items():
        p = (n["X"], n["Y"], n["Z"])
        key = (round(p[0] / tol), round(p[1] / tol), round(p[2] / tol))
        buckets.setdefault(key, []).append((int(nid), p))
    dup_ids = set()
    for key, items in buckets.items():
        cand = list(items)
        for dk in ((0, 0, 1), (0, 1, 0), (1, 0, 0), (0, 1, 1), (1, 0, 1),
                   (1, 1, 0), (1, 1, 1)):
            cand += buckets.get((key[0] + dk[0], key[1] + dk[1], key[2] + dk[2]), [])
        for (i1, p1), (i2, p2) in combinations(cand, 2):
            if i1 != i2 and _dist(p1, p2) < tol:
                dup_ids.add(i1)
                dup_ids.add(i2)
    if not dup_ids:
        return []
    return [Finding("G1", "중복 절점", SEVERITY_ERROR, "NODE", sorted(dup_ids),
                    f"좌표가 {ctx.cfg.tol_merge_mm}mm 이내로 겹치는 절점 {len(dup_ids)}개.",
                    "Node Merge 로 중복 절점을 병합.")]


@register("G2", "중복 요소")
def g2_duplicate_elems(ctx):
    seen, dup = {}, set()
    for eid, e in ctx.elems.items():
        ns = tuple(sorted(ctx.elem_nodes(e)))
        if len(ns) < 2:
            continue
        key = (str(e.get("TYPE", "")).upper(), ns)
        if key in seen:
            dup.add(int(seen[key]))
            dup.add(int(eid))
        else:
            seen[key] = eid
    if not dup:
        return []
    return [Finding("G2", "중복 요소", SEVERITY_ERROR, "ELEM", sorted(dup),
                    f"동일 타입·동일 절점 연결의 중복 요소 {len(dup)}개.", "중복 요소 삭제.")]


@register("G3", "영길이 부재")
def g3_zero_length(ctx):
    tol = ctx.cfg.tol_zero_m
    bad = []
    for eid, ns in _line_elems(ctx).items():
        p1, p2 = ctx.node_xyz(ns[0]), ctx.node_xyz(ns[1])
        if p1 and p2 and _dist(p1, p2) < tol:
            bad.append(int(eid))
    if not bad:
        return []
    return [Finding("G3", "영길이 부재", SEVERITY_ERROR, "ELEM", sorted(bad),
                    f"두 절점 간 거리 < {ctx.cfg.tol_zero_mm}mm 인 부재 {len(bad)}개.",
                    "요소 삭제 또는 절점 좌표 수정.")]


def _unit_vec(p1, p2):
    d = [b - a for a, b in zip(p1, p2)]
    L = math.sqrt(sum(x * x for x in d))
    return ([x / L for x in d], L) if L > 1e-12 else (None, 0.0)


@register("G4", "부재 부분겹침(콜리니어)")
def g4_partial_overlap(ctx):
    cos_tol = math.cos(math.radians(ctx.cfg.collinear_deg))
    segs = []
    for eid, ns in _line_elems(ctx).items():
        p1, p2 = ctx.node_xyz(ns[0]), ctx.node_xyz(ns[1])
        if not (p1 and p2):
            continue
        u, L = _unit_vec(p1, p2)
        if u:
            segs.append((int(eid), p1, p2, u, L))
    pairs = set()
    for i in range(len(segs)):
        e1, a1, b1, u1, L1 = segs[i]
        for j in range(i + 1, len(segs)):
            e2, a2, b2, u2, L2 = segs[j]
            if abs(sum(x * y for x, y in zip(u1, u2))) < cos_tol:
                continue
            cross = [a2[k] - a1[k] for k in range(3)]
            along = sum(c * u1[k] for k, c in enumerate(cross))
            perp = math.sqrt(max(0.0, sum(c * c for c in cross) - along * along))
            if perp > ctx.cfg.tol_merge_m:
                continue
            t = sorted([0.0, L1, along,
                        sum((b2[k] - a1[k]) * u1[k] for k in range(3))])
            ov = min(L1, t[2]) - max(0.0, t[1])
            if ov > ctx.cfg.overlap_min_m:
                pairs.add((e1, e2))
    if not pairs:
        return []
    ids = sorted({e for pr in pairs for e in pr})
    return [Finding("G4", "부재 부분겹침(콜리니어)", SEVERITY_WARN, "ELEM", ids,
                    f"동일선상에서 10mm 초과 겹치는 부재 쌍 {len(pairs)}건.",
                    "겹친 부재 정리 또는 분할점 절점 추가.")]


def _referenced_nodes(ctx):
    ref = set()
    for e in ctx.elems.values():
        ref.update(ctx.elem_nodes(e))
    ref.update(int(k) for k in ctx.cons)
    ref.update(int(k) for k in ctx.nspr)
    ref.update(int(k) for k in ctx.gspr)
    ref.update(int(k) for k in ctx.ssps)
    ref.update(int(k) for k in ctx.sdsp)
    ref.update(int(k) for k in ctx.nmas)
    ref.update(int(k) for k in ctx.ltom)
    for r in ctx.rigd.values():
        for it in r.get("ITEMS", []) or []:
            ref.update(int(x) for x in it.get("S_NODE", []) or [])
    ref.update(int(k) for k in ctx.rigd)
    for el in ctx.elnk.values():
        ref.update(int(x) for x in el.get("NODE", []) or [])
    ref.update(int(k) for k in ctx.cnld)
    return ref


@register("G5", "완전 고립 절점")
def g5_isolated_nodes(ctx):
    ref = _referenced_nodes(ctx)
    iso = [int(nid) for nid in ctx.nodes if int(nid) not in ref]
    if not iso:
        return []
    return [Finding("G5", "완전 고립 절점", SEVERITY_WARN, "NODE", sorted(iso),
                    f"어떤 요소·지점·강체·하중·질량에도 참조되지 않는 절점 {len(iso)}개.",
                    "불필요하면 삭제, 아니면 연결/지점 확인.")]


@register("G6", "유리절점(dangling)")
def g6_dangling_nodes(ctx):
    deg = {}
    for ns in _line_elems(ctx).values():
        for n in ns:
            deg[n] = deg.get(n, 0) + 1
    supported = set(int(k) for k in ctx.cons) | set(int(k) for k in ctx.nspr)
    supported |= set(int(k) for k in ctx.gspr) | set(int(k) for k in ctx.ssps)
    for r in ctx.rigd.values():
        for it in r.get("ITEMS", []) or []:
            supported.update(int(x) for x in it.get("S_NODE", []) or [])
    supported.update(int(k) for k in ctx.rigd)
    dang = sorted(n for n, d in deg.items() if d == 1 and n not in supported)
    if not dang:
        return []
    return [Finding("G6", "유리절점(dangling)", SEVERITY_WARN, "NODE", dang,
                    f"단 하나의 부재 끝에만 연결되고 지점·강체가 없는 절점 {len(dang)}개.",
                    "연결 누락 여부 확인.")]


@register("G7", "미접합 교차부재")
def g7_uncoined_intersections(ctx):
    segs = []
    for eid, ns in _line_elems(ctx).items():
        p1, p2 = ctx.node_xyz(ns[0]), ctx.node_xyz(ns[1])
        if p1 and p2:
            segs.append((int(eid), p1, p2))
    node_pts = [(n["X"], n["Y"], n["Z"]) for n in ctx.nodes.values()]
    tol = max(ctx.cfg.tol_merge_m, 1e-6)
    hits = set()
    for i in range(len(segs)):
        e1, a1, b1 = segs[i]
        d1 = [b1[k] - a1[k] for k in range(3)]
        for j in range(i + 1, len(segs)):
            e2, a2, b2 = segs[j]
            d2 = [b2[k] - a2[k] for k in range(3)]
            ip = _segment_intersection(a1, d1, a2, d2, tol)
            if ip and not any(_dist(ip, npt) < tol for npt in node_pts):
                hits.add((e1, e2))
    if not hits:
        return []
    ids = sorted({e for pr in hits for e in pr})
    return [Finding("G7", "미접합 교차부재", SEVERITY_INFO, "ELEM", ids,
                    f"교차점에 절점이 없는 부재 쌍 {len(hits)}건(검토 필요).",
                    "실제 접합이면 교차점에 절점 추가 후 분할.")]


def _segment_intersection(a1, d1, a2, d2, tol):
    def dot(u, v):
        return sum(x * y for x, y in zip(u, v))
    w0 = [a1[k] - a2[k] for k in range(3)]
    a, b, c = dot(d1, d1), dot(d1, d2), dot(d2, d2)
    d, e = dot(d1, w0), dot(d2, w0)
    den = a * c - b * b
    if abs(den) < 1e-12 or a < 1e-12 or c < 1e-12:
        return None
    t = (b * e - c * d) / den
    u = (a * e - b * d) / den
    if not (1e-6 < t < 1 - 1e-6 and 1e-6 < u < 1 - 1e-6):
        return None
    p = [a1[k] + t * d1[k] for k in range(3)]
    q = [a2[k] + u * d2[k] for k in range(3)]
    return p if _dist(p, q) <= tol else None
