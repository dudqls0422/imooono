"""물성 점검 P1~P3."""
from __future__ import annotations

from . import Finding, SEVERITY_ERROR, register


@register("P1", "재료 미지정")
def p1_material_missing(ctx):
    bad = []
    for eid, e in ctx.elems.items():
        ref = e.get("MATL")
        if ref in (0, "0", None, "") or str(ref) not in ctx.matls:
            bad.append(int(eid))
    if not bad:
        return []
    return [Finding("P1", "재료 미지정", SEVERITY_ERROR, "ELEM", sorted(bad),
                    f"MATL 참조가 0이거나 존재하지 않는 요소 {len(bad)}개.",
                    "요소에 유효한 재료 번호 지정.")]


@register("P2", "단면·두께 미지정")
def p2_section_missing(ctx):
    bad = []
    for eid, e in ctx.elems.items():
        ref = e.get("SECT")
        if str(ref) in ctx.sects or str(ref) in ctx.thiks:
            continue
        bad.append(int(eid))
    if not bad:
        return []
    return [Finding("P2", "단면·두께 미지정", SEVERITY_ERROR, "ELEM", sorted(bad),
                    f"SECT/THIK 참조가 0이거나 존재하지 않는 요소 {len(bad)}개.",
                    "요소에 유효한 단면/두께 번호 지정.")]


def _matl_e_and_density(m):
    params = m.get("PARAM")
    rows = params if isinstance(params, list) else ([params] if params else [])
    e = den = mass = None
    for r in rows:
        if not isinstance(r, dict):
            continue
        if r.get("ELAST") is not None:
            e = r.get("ELAST")
        if r.get("DEN") is not None:
            den = r.get("DEN")
        if r.get("MASS") is not None:
            mass = r.get("MASS")
    return e, den, mass


@register("P3", "비정상 물성")
def p3_abnormal_material(ctx):
    uses_selfweight = any(
        any(abs(float(v)) > 1e-12 for v in (b.get("FV") or [0, 0, 0]))
        for b in ctx.bodf.values()
    )
    used_matls = {str(e.get("MATL")) for e in ctx.elems.values()}
    bad = []
    for mid, m in ctx.matls.items():
        if str(mid) not in used_matls:
            continue
        e, den, mass = _matl_e_and_density(m)
        try:
            if e is not None and float(e) <= 0:
                bad.append(int(mid))
                continue
        except (TypeError, ValueError):
            pass
        if uses_selfweight:
            d = 0.0
            for v in (den, mass):
                try:
                    d = max(d, abs(float(v)))
                except (TypeError, ValueError):
                    pass
            if d <= 1e-12:
                bad.append(int(mid))
    if not bad:
        return []
    return [Finding("P3", "비정상 물성", SEVERITY_ERROR, "MODEL", sorted(set(bad)),
                    f"E ≤ 0 이거나, 자중 케이스가 있는데 밀도/단위중량이 0인 재료 {len(set(bad))}개.",
                    "재료 물성(탄성계수·밀도) 확인.")]
