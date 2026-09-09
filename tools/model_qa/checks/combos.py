"""하중조합 점검 K1~K3."""
from __future__ import annotations

from . import Finding, SEVERITY_ERROR, SEVERITY_WARN, SEVERITY_INFO, register

WIND_TYPES = {"W", "WA", "WX", "WY"}
SEIS_TYPES = {"E", "ES", "EX", "EY", "RS"}


def _all_combos(ctx):
    out = []
    for sub, coll in ctx.lcom.items():
        for cid, c in coll.items():
            out.append((sub, cid, c))
    return out


def _is_active(c):
    return str(c.get("ACTIVE", "ACTIVE")).upper() != "INACTIVE"


def _combo_lcnames(c):
    return [str(t.get("LCNAME")) for t in (c.get("vCOMB", []) or []) if t.get("LCNAME")]


def _splc_names(ctx):
    return {str(v.get("NAME")) for v in getattr(ctx, "splc", {}).values() if v.get("NAME")}


@register("K1", "조합 부실")
def k1_weak_combos(ctx):
    combos = _all_combos(ctx)
    if not any(ctx.lcom.values()):
        return [Finding("K1", "조합 부실", SEVERITY_WARN, "MODEL", [],
                        "하중조합(LCOM-*)이 하나도 없음.", "설계용 하중조합 정의.")]
    active = [(s, cid, c) for s, cid, c in combos if _is_active(c)]
    findings = []
    if not active:
        findings.append(Finding("K1", "조합 부실", SEVERITY_WARN, "COMBO", [],
                                f"정의된 조합 {len(combos)}개가 전부 INACTIVE.",
                                "필요한 조합을 ACTIVE 로 전환."))
    single = sorted(int(cid) for s, cid, c in active if len(_combo_lcnames(c)) <= 1)
    if single and len(single) == len(active):
        findings.append(Finding("K1", "조합 부실", SEVERITY_WARN, "COMBO", single,
                                f"활성 조합 {len(active)}개가 모두 단일 케이스로만 구성.",
                                "실제 설계 조합(계수 조합)이 맞는지 확인."))
    inactive_empty = sorted(int(cid) for s, cid, c in combos
                            if not _is_active(c) and len(c.get("vCOMB", []) or []) == 0)
    if inactive_empty:
        findings.append(Finding("K1", "조합 부실", SEVERITY_INFO, "COMBO", inactive_empty,
                                f"INACTIVE 이면서 항이 비어 있는 조합 {len(inactive_empty)}개.",
                                "정리 대상(참고)."))
    return findings


@register("K2", "풍·지진 조합 미포함")
def k2_wind_seis_not_combined(ctx):
    if not ctx.stld:
        return []
    in_combo = set()
    for s, cid, c in _all_combos(ctx):
        in_combo.update(_combo_lcnames(c))
    ws_cases = {}
    for c in ctx.stld.values():
        t = str(c.get("TYPE", "")).upper()
        nm = str(c.get("NAME", ""))
        if not nm:
            continue
        if t in WIND_TYPES:
            ws_cases[nm] = "풍"
        elif t in SEIS_TYPES:
            ws_cases[nm] = "지진"
    for nm in _splc_names(ctx):
        ws_cases.setdefault(nm, "응답스펙트럼")
    missing = sorted(nm for nm in ws_cases if nm not in in_combo)
    if not missing:
        return []
    return [Finding("K2", "풍·지진 조합 미포함", SEVERITY_WARN, "LOADCASE", missing,
                    "풍/지진 하중케이스가 어떤 하중조합에도 포함되지 않음: "
                    + ", ".join(f"{n}({ws_cases[n]})" for n in missing),
                    "풍/지진 케이스를 설계 조합에 반영.")]


@register("K3", "없는 케이스 참조 조합")
def k3_combo_bad_ref(ctx):
    stld_names = {str(c.get("NAME")) for c in ctx.stld.values() if c.get("NAME")}
    combo_names = {str(c.get("NAME")) for s, cid, c in _all_combos(ctx) if c.get("NAME")}
    known = stld_names | combo_names | _splc_names(ctx)
    bad = []
    for s, cid, c in _all_combos(ctx):
        for term in c.get("vCOMB", []) or []:
            nm = str(term.get("LCNAME", ""))
            anal = str(term.get("ANAL", "")).upper()
            if not nm:
                continue
            pool = combo_names if anal in ("CB", "CBC", "CBS") else known
            if nm not in pool and nm not in known:
                bad.append((s, int(cid), nm))
    if not bad:
        return []
    ids = sorted({cid for _s, cid, _n in bad})
    detail = ", ".join(f"{s}#{cid}->'{nm}'" for s, cid, nm in bad[:20])
    return [Finding("K3", "없는 케이스 참조 조합", SEVERITY_ERROR, "COMBO", ids,
                    f"존재하지 않는 케이스/조합을 참조하는 조합 {len(bad)}건: {detail}",
                    "참조 케이스명 오타·삭제 여부 확인.")]
