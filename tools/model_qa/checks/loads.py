"""하중 점검 L1~L3."""
from __future__ import annotations

from . import Finding, SEVERITY_WARN, SEVERITY_INFO, register


def _load_case_names_with_loads(ctx):
    used = set()
    for coll in (ctx.cnld, ctx.bmld, ctx.pres):
        for row in coll.values():
            for it in row.get("ITEMS", []) or []:
                if it.get("LCNAME"):
                    used.add(str(it["LCNAME"]))
    for b in ctx.bodf.values():
        if b.get("LCNAME"):
            used.add(str(b["LCNAME"]))
    return used


@register("L1", "빈 하중케이스")
def l1_empty_load_cases(ctx):
    if not ctx.stld:
        return []
    used = _load_case_names_with_loads(ctx)
    empty = sorted(int(cid) for cid, c in ctx.stld.items()
                   if str(c.get("NAME", "")) and str(c["NAME"]) not in used)
    if not empty:
        return []
    names = ", ".join(str(ctx.stld[str(i)].get("NAME")) for i in empty if str(i) in ctx.stld)
    return [Finding("L1", "빈 하중케이스", SEVERITY_WARN, "LOADCASE", empty,
                    f"정의만 되고 실제 하중이 하나도 없는 정적 하중케이스 {len(empty)}개: {names}",
                    "미사용 케이스 삭제 또는 하중 입력.")]


@register("L2", "자중 케이스 누락")
def l2_selfweight_missing(ctx):
    has_grav = any(
        any(abs(float(v)) > 1e-12 for v in (b.get("FV") or [0, 0, 0]))
        for b in ctx.bodf.values()
    )
    if has_grav:
        return []
    return [Finding("L2", "자중 케이스 누락", SEVERITY_WARN, "MODEL", [],
                    "Self-Weight(BODF) 중력 하중이 정의된 케이스가 없음.",
                    "고정하중 케이스에 자중(FV=[0,0,-1] 등) 적용 여부 확인.")]


@register("L3", "조합 미포함 사용자 케이스")
def l3_case_not_in_combo(ctx):
    if not ctx.stld:
        return []
    in_combo = set()
    for coll in ctx.lcom.values():
        for c in coll.values():
            for term in c.get("vCOMB", []) or []:
                if term.get("LCNAME"):
                    in_combo.add(str(term["LCNAME"]))
    orphan = sorted(int(cid) for cid, c in ctx.stld.items()
                    if str(c.get("NAME", "")) and str(c["NAME"]) not in in_combo)
    if not orphan:
        return []
    names = ", ".join(str(ctx.stld[str(i)].get("NAME")) for i in orphan if str(i) in ctx.stld)
    return [Finding("L3", "조합 미포함 사용자 케이스", SEVERITY_INFO, "LOADCASE", orphan,
                    f"어떤 하중조합에도 포함되지 않은 하중케이스 {len(orphan)}개: {names}",
                    "설계에 필요하면 해당 케이스를 조합에 추가.")]
