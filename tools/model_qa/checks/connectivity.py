"""연결/강체/다이어프램 점검 C1~C3."""
from __future__ import annotations

from . import Finding, SEVERITY_ERROR, SEVERITY_WARN, SEVERITY_INFO, register


def _rigid_edges(ctx):
    edges = []
    for mkey, r in ctx.rigd.items():
        try:
            master = int(mkey)
        except (TypeError, ValueError):
            continue
        for it in r.get("ITEMS", []) or []:
            for s in it.get("S_NODE", []) or []:
                edges.append((master, int(s)))
    for el in ctx.elnk.values():
        if str(el.get("LINK", "")).upper() == "RIGID":
            ns = el.get("NODE") or []
            if len(ns) == 2:
                edges.append((int(ns[0]), int(ns[1])))
    return edges


@register("C1", "강체 순환·중복마스터")
def c1_rigid_cycles(ctx):
    edges = _rigid_edges(ctx)
    if not edges:
        return []
    masters_of, adj = {}, {}
    for m, s in edges:
        masters_of.setdefault(s, set()).add(m)
        adj.setdefault(m, []).append(s)
    findings = []

    multi = sorted(s for s, ms in masters_of.items() if len(ms) >= 2)
    if multi:
        findings.append(Finding(
            "C1", "강체 순환·중복마스터", SEVERITY_ERROR, "NODE", multi,
            f"한 슬레이브 절점에 마스터가 2개 이상인 경우 {len(multi)}건.",
            "슬레이브가 여러 강체에 종속되지 않도록 정리."))

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {}
    cyc_nodes = set()

    def dfs(u):
        color[u] = GRAY
        for v in adj.get(u, []):
            cv = color.get(v, WHITE)
            if cv == GRAY:
                cyc_nodes.add(u)
                cyc_nodes.add(v)
            elif cv == WHITE:
                dfs(v)
        color[u] = BLACK

    for n in list(adj):
        if color.get(n, WHITE) == WHITE:
            dfs(n)
    if cyc_nodes:
        findings.append(Finding(
            "C1", "강체 순환·중복마스터", SEVERITY_ERROR, "NODE", sorted(cyc_nodes),
            f"강체 마스터-슬레이브 그래프에 순환 존재({len(cyc_nodes)}절점 관여).",
            "강체 링크 체인의 순환 제거."))
    return findings


@register("C2", "다이어프램 미할당 층")
def c2_diaphragm(ctx):
    if not ctx.stor:
        return []
    flags = {str(sid): bool(s.get("bFLOOR_DIAPHRAGM", False))
             for sid, s in ctx.stor.items()}
    n_true = sum(1 for v in flags.values() if v)
    n_total = len(flags)
    drls_nodes = sum(len(v) if isinstance(v, (list, dict)) else 1
                     for v in ctx.drls.values())

    if n_true == n_total:
        return []
    if n_true == 0:
        return [Finding("C2", "다이어프램 미할당 층", SEVERITY_INFO, "MODEL", [],
                        f"층 정의 {n_total}개가 있으나 강막(bFLOOR_DIAPHRAGM)이 전부 미사용. "
                        f"(유연격막/수동 다이어프램 모델일 수 있음. DRLS 해제절점 {drls_nodes}개.)",
                        "의도된 유연격막이면 무시. 아니면 층별 강막 지정 검토.")]
    off = sorted(int(k) for k, v in flags.items() if not v)
    return [Finding("C2", "다이어프램 미할당 층", SEVERITY_WARN, "MODEL", off,
                    f"층 {n_total}개 중 {n_true}개만 강막 지정. 나머지 {len(off)}개 층 미지정(불일치).",
                    "층별 강막 적용 여부를 일관되게 설정.")]


@register("C3", "삭제 ID 참조 하중")
def c3_dangling_load_refs(ctx):
    node_ids = set(int(k) for k in ctx.nodes)
    elem_ids = set(int(k) for k in ctx.elems)
    bad_nodes, bad_elems = set(), set()
    for k in ctx.cnld:
        if int(k) not in node_ids:
            bad_nodes.add(int(k))
    for coll in (ctx.bmld, ctx.pres):
        for k in coll:
            if int(k) not in elem_ids:
                bad_elems.add(int(k))
    findings = []
    if bad_nodes:
        findings.append(Finding("C3", "삭제 ID 참조 하중", SEVERITY_ERROR, "NODE",
                                sorted(bad_nodes),
                                f"존재하지 않는 절점에 절점하중이 지정됨 {len(bad_nodes)}건.",
                                "해당 하중 삭제 또는 절점 복구."))
    if bad_elems:
        findings.append(Finding("C3", "삭제 ID 참조 하중", SEVERITY_ERROR, "ELEM",
                                sorted(bad_elems),
                                f"존재하지 않는 요소에 보/압력 하중이 지정됨 {len(bad_elems)}건.",
                                "해당 하중 삭제 또는 요소 복구."))
    return findings
