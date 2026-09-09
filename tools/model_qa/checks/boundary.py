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


# 각 전역 회전축(RX=3/RY=4/RZ=5)을 커플로 저항하는 데 필요한
# (병진 DOF 인덱스 쌍, 커플 팔이 놓이는 좌표축 인덱스 쌍).
#   RX: YZ 평면 이동 → DY/DZ 병진구속이 서로 다른 Y 또는 Z 위치에.
#   RY: XZ 평면 이동 → DX/DZ 병진구속이 서로 다른 X 또는 Z 위치에.
#   RZ: XY 평면 이동 → DX/DY 병진구속이 서로 다른 X 또는 Y 위치에.
_ROT_COUPLE = {3: ((1, 2), (1, 2)), 4: ((0, 2), (0, 2)), 5: ((0, 1), (0, 1))}


def _support_dofs_and_points(ctx):
    """[(xyz|None, {구속 DOF 인덱스 0..5})] — CONS + NSPR/GSPR 스프링."""
    out = []
    for nid, c in ctx.cons.items():
        dofs = _cons_constrained_dofs(c)
        if dofs:
            out.append((ctx.node_xyz(nid), dofs))
    for coll in (ctx.nspr, ctx.gspr):
        for nid, row in coll.items():
            dofs = set()
            for it in row.get("ITEMS", []) or []:
                sdr = it.get("SDR") or []
                for i in range(min(6, len(sdr))):
                    try:
                        if abs(float(sdr[i])) > 0:
                            dofs.add(i)
                    except (TypeError, ValueError):
                        pass
            if dofs:
                out.append((ctx.node_xyz(nid), dofs))
    return out


def _model_span(ctx):
    exts = []
    for k in ("X", "Y", "Z"):
        vals = [n[k] for n in ctx.nodes.values() if k in n]
        if vals:
            exts.append(max(vals) - min(vals))
    return max(exts) if exts else 0.0


def _rotation_status(sups, axis, tol, model_span):
    """axis 전역 회전이 (a)직접 구속 / (b)병진구속 커플로 저항되는가.
    반환: 'direct' | 'couple' | 'marginal' | 'free'."""
    if any(axis in dofs for _p, dofs in sups):
        return "direct"
    (t1, t2), (c1, c2) = _ROT_COUPLE[axis]
    pos = [p for p, dofs in sups
           if p is not None and (t1 in dofs or t2 in dofs)]
    if len(pos) < 2:
        return "free"
    arm = max(max(v[c] for v in pos) - min(v[c] for v in pos) for c in (c1, c2))
    strong = max(tol * 50.0, 0.01 * model_span)
    if arm >= strong:
        return "couple"
    if arm > tol:
        return "marginal"
    return "free"


@register("B2", "전역 강체거동 미구속")
def b2_global_rigid_body(ctx):
    sups = _support_dofs_and_points(ctx)
    if not sups:
        return []  # 지점 자체가 없음 → B1 이 담당
    tol = max(ctx.cfg.tol_merge_m, 1e-9)
    span = _model_span(ctx)

    trans_free = [_DOF_NAMES[i] for i in range(3)
                  if not any(i in dofs for _p, dofs in sups)]
    rot_free, rot_marginal = [], []
    for axis in (3, 4, 5):
        st = _rotation_status(sups, axis, tol, span)
        if st == "free":
            rot_free.append(_DOF_NAMES[axis])
        elif st == "marginal":
            rot_marginal.append(_DOF_NAMES[axis])

    findings = []
    err_dofs = trans_free + rot_free
    if err_dofs:
        findings.append(Finding(
            "B2", "전역 강체거동 미구속", SEVERITY_ERROR, "MODEL", [],
            f"전역 강체거동을 저항하지 못하는 자유도: {', '.join(err_dofs)}. "
            "직접 구속도 없고, 분포된 지점의 병진구속 커플로도 저항되지 않음.",
            "해당 방향을 구속하는 지점을 추가하거나 지점 배치를 확인."))
    if rot_marginal:
        findings.append(Finding(
            "B2", "전역 강체거동 미구속", SEVERITY_WARN, "MODEL", [],
            f"전역 회전 {', '.join(rot_marginal)} 이(가) 직접 구속되지 않고, "
            "지점 커플의 팔이 매우 짧아 회전 저항이 취약함(지점이 거의 한 점/한 선에 몰림).",
            "회전 구속 지점 추가 또는 지점 간 이격 확인."))
    return findings


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
