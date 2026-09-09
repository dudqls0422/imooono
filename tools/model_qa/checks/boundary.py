"""경계조건 점검 B1~B3."""
from __future__ import annotations

from . import Finding, SEVERITY_ERROR, SEVERITY_WARN, register

_DOF_NAMES = ["DX", "DY", "DZ", "RX", "RY", "RZ"]


def _spring_nodes(ctx):
    ids = set()
    for coll in (ctx.nspr, ctx.gspr, ctx.ssps):
        ids.update(int(k) for k in coll)
    return ids


def _cons_constrained_dofs(cons_item):
    out = set()
    for it in cons_item.get("ITEMS", []) or []:
        s = str(it.get("CONSTRAINT", ""))
        for i in range(min(6, len(s))):
            if s[i] not in ("0", " ", ""):
                out.add(i)
    return out


@register("B1", "지점 전무")
def b1_no_supports(ctx):
    if ctx.cons or _spring_nodes(ctx) or ctx.sdsp:
        return []
    return [Finding("B1", "지점 전무", SEVERITY_ERROR, "MODEL", [],
                    "구속 지점(CONS)·스프링 지점(NSPR/GSPR/SSPS)·강제변위 지점이 하나도 없음.",
                    "지지 조건을 정의하지 않으면 해석이 특이(singular)해짐.")]


@register("B2", "전역 강체거동 미구속")
def b2_global_rigid_body(ctx):
    if not (ctx.cons or _spring_nodes(ctx)):
        return []
    constrained = set()
    for c in ctx.cons.values():
        constrained |= _cons_constrained_dofs(c)
    for coll in (ctx.nspr, ctx.gspr):
        for row in coll.values():
            for it in row.get("ITEMS", []) or []:
                sdr = it.get("SDR") or []
                for i in range(min(6, len(sdr))):
                    try:
                        if abs(float(sdr[i])) > 0:
                            constrained.add(i)
                    except (TypeError, ValueError):
                        pass
    free = [_DOF_NAMES[i] for i in range(6) if i not in constrained]
    if not free:
        return []
    return [Finding("B2", "전역 강체거동 미구속", SEVERITY_ERROR, "MODEL", [],
                    f"전역 자유도 중 어디에서도 구속되지 않은 방향: {', '.join(free)}. "
                    "모델이 강체 이동/회전 가능(특이 강성).",
                    "해당 방향을 구속하는 지점 추가.")]


@register("B3", "유령절점 지점")
def b3_ghost_supports(ctx):
    bad = []
    for coll in (ctx.cons, ctx.nspr, ctx.gspr, ctx.ssps, ctx.sdsp):
        for k in coll:
            if str(k) not in ctx.nodes:
                bad.append(int(k))
    if not bad:
        return []
    return [Finding("B3", "유령절점 지점", SEVERITY_WARN, "NODE", sorted(set(bad)),
                    f"존재하지 않는 절점 ID 에 지점/스프링이 지정됨 {len(set(bad))}건.",
                    "절점 삭제 후 남은 지점 정의 정리.")]
