"""판요소 메시 점검 M1~M3. 판요소가 없으면 전부 스킵([] 반환)."""
from __future__ import annotations

import math

from . import Finding, SEVERITY_ERROR, SEVERITY_WARN, register

PLATE_TYPES = {"PLATE", "PLANESTRESS", "PLANESTRAIN", "WALL", "MEMBRANE"}


def _plate_elems(ctx):
    out = {}
    for eid, e in ctx.elems.items():
        if str(e.get("TYPE", "")).upper() not in PLATE_TYPES:
            continue
        ns = ctx.elem_nodes(e)
        pts = [ctx.node_xyz(n) for n in ns]
        if len(pts) in (3, 4) and all(p is not None for p in pts):
            out[int(eid)] = (ns, pts)
    return out


def _edge_lengths(pts):
    n = len(pts)
    return [math.dist(pts[i], pts[(i + 1) % n]) for i in range(n)]


def _interior_angles(pts):
    n = len(pts)
    angs = []
    for i in range(n):
        a, b, c = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
        v1 = [a[k] - b[k] for k in range(3)]
        v2 = [c[k] - b[k] for k in range(3)]
        n1 = math.sqrt(sum(x * x for x in v1))
        n2 = math.sqrt(sum(x * x for x in v2))
        if n1 < 1e-12 or n2 < 1e-12:
            angs.append(0.0)
            continue
        cosv = max(-1.0, min(1.0, sum(x * y for x, y in zip(v1, v2)) / (n1 * n2)))
        angs.append(math.degrees(math.acos(cosv)))
    return angs


@register("M1", "판 종횡비")
def m1_aspect_ratio(ctx):
    plates = _plate_elems(ctx)
    if not plates:
        return []
    warn, err = [], []
    for eid, (ns, pts) in plates.items():
        L = [x for x in _edge_lengths(pts) if x > 1e-9]
        if not L:
            continue
        ar = max(L) / min(L)
        if ar > ctx.cfg.aspect_err:
            err.append(eid)
        elif ar > ctx.cfg.aspect_warn:
            warn.append(eid)
    out = []
    if err:
        out.append(Finding("M1", "판 종횡비", SEVERITY_ERROR, "PLATE", sorted(err),
                           f"종횡비 > {ctx.cfg.aspect_err} 인 판요소 {len(err)}개.",
                           "메시 세분 또는 재분할."))
    if warn:
        out.append(Finding("M1", "판 종횡비", SEVERITY_WARN, "PLATE", sorted(warn),
                           f"종횡비 > {ctx.cfg.aspect_warn} 인 판요소 {len(warn)}개.",
                           "가능하면 메시 개선."))
    return out


@register("M2", "판 내각 이상")
def m2_interior_angles(ctx):
    plates = _plate_elems(ctx)
    if not plates:
        return []
    bad = [eid for eid, (ns, pts) in plates.items()
           if any(a < 30.0 or a > 150.0 for a in _interior_angles(pts))]
    if not bad:
        return []
    return [Finding("M2", "판 내각 이상", SEVERITY_WARN, "PLATE", sorted(bad),
                    f"내각이 30°~150° 범위를 벗어난 판요소 {len(bad)}개.", "왜곡된 요소 재메시.")]


@register("M3", "자유모서리 미봉합")
def m3_free_edge_mismatch(ctx):
    plates = _plate_elems(ctx)
    if not plates:
        return []
    edge_use, edge_owner = {}, {}
    for eid, (ns, pts) in plates.items():
        m = len(ns)
        for i in range(m):
            key = tuple(sorted((int(ns[i]), int(ns[(i + 1) % m]))))
            edge_use[key] = edge_use.get(key, 0) + 1
            edge_owner.setdefault(key, []).append(eid)
    free_edges = [(k, edge_owner[k][0]) for k, v in edge_use.items() if v == 1]
    tol = max(ctx.cfg.tol_merge_m, 1e-6)

    def mid(k):
        p1, p2 = ctx.node_xyz(k[0]), ctx.node_xyz(k[1])
        return tuple((a + b) / 2 for a, b in zip(p1, p2)) if p1 and p2 else None

    mids = [(k, eid, mid(k)) for k, eid in free_edges]
    bad = set()
    for i in range(len(mids)):
        k1, e1, m1 = mids[i]
        if m1 is None:
            continue
        for j in range(i + 1, len(mids)):
            k2, e2, m2 = mids[j]
            if m2 is None or set(k1) == set(k2):
                continue
            if math.dist(m1, m2) < tol:
                bad.add(e1)
                bad.add(e2)
    if not bad:
        return []
    return [Finding("M3", "자유모서리 미봉합", SEVERITY_ERROR, "PLATE", sorted(bad),
                    f"인접 판이 공유 절점 없이 모서리만 맞닿은 경우 {len(bad)}개 요소 관여.",
                    "경계 절점 병합 또는 메시 정합화.")]
