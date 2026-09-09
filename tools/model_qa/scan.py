"""오케스트레이터: 리소스 수집 → 단위 정규화 → 체크 실행 → findings."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from .checks import CHECK_REGISTRY, Finding, SEVERITY_INFO, load_all_checks
from .client import ReadOnlyClient, ResourceUnavailable
from .config import ScanConfig

_DIST_TO_M = {"M": 1.0, "CM": 0.01, "MM": 0.001, "FT": 0.3048, "IN": 0.0254}
_FORCE_TO_KN = {"KN": 1.0, "N": 0.001, "KGF": 0.00980665, "TONF": 9.80665,
                "KIPS": 4.4482216152605, "LBF": 0.0044482216152605}

COLLECTIONS = {
    "nodes": "NODE", "elems": "ELEM", "matls": "MATL", "sects": "SECT",
    "thiks": "THIK", "cons": "CONS", "nspr": "NSPR", "gspr": "GSPR",
    "gstp": "GSTP", "ssps": "SSPS", "sdsp": "SDSP", "rigd": "RIGD",
    "elnk": "ELNK", "stor": "STOR", "drls": "DRLS", "stld": "STLD",
    "cnld": "CNLD", "bmld": "BMLD", "pres": "PRES", "bodf": "BODF",
    "grup": "GRUP", "bngr": "BNGR", "ldgr": "LDGR", "nmas": "NMAS",
    "ltom": "LTOM", "stag": "STAG", "splc": "SPLC",
    "swind": "SWIND", "sseis": "SSEIS", "spfc": "SPFC", "posl": "POSL",
}
LCOM_KEYS = ["LCOM-GEN", "LCOM-CONC", "LCOM-STEEL", "LCOM-SRC",
             "LCOM-STLCOMP", "LCOM-SEISMIC"]

PLATE_TYPES = {"PLATE", "PLANESTRESS", "PLANESTRAIN", "WALL", "MEMBRANE"}


def _to_int(s, default=None):
    try:
        return int(s)
    except (TypeError, ValueError):
        return default


@dataclass
class ScanContext:
    cfg: ScanConfig
    unit_raw: Dict[str, str] = field(default_factory=dict)
    dist_factor: float = 1.0
    force_factor: float = 1.0

    nodes: Dict[str, dict] = field(default_factory=dict)
    elems: Dict[str, dict] = field(default_factory=dict)
    matls: Dict[str, dict] = field(default_factory=dict)
    sects: Dict[str, dict] = field(default_factory=dict)
    thiks: Dict[str, dict] = field(default_factory=dict)
    cons: Dict[str, dict] = field(default_factory=dict)
    nspr: Dict[str, dict] = field(default_factory=dict)
    gspr: Dict[str, dict] = field(default_factory=dict)
    gstp: Dict[str, dict] = field(default_factory=dict)
    ssps: Dict[str, dict] = field(default_factory=dict)
    sdsp: Dict[str, dict] = field(default_factory=dict)
    rigd: Dict[str, dict] = field(default_factory=dict)
    elnk: Dict[str, dict] = field(default_factory=dict)
    stor: Dict[str, dict] = field(default_factory=dict)
    drls: Dict[str, dict] = field(default_factory=dict)
    stld: Dict[str, dict] = field(default_factory=dict)
    cnld: Dict[str, dict] = field(default_factory=dict)
    bmld: Dict[str, dict] = field(default_factory=dict)
    pres: Dict[str, dict] = field(default_factory=dict)
    bodf: Dict[str, dict] = field(default_factory=dict)
    grup: Dict[str, dict] = field(default_factory=dict)
    bngr: Dict[str, dict] = field(default_factory=dict)
    ldgr: Dict[str, dict] = field(default_factory=dict)
    nmas: Dict[str, dict] = field(default_factory=dict)
    ltom: Dict[str, dict] = field(default_factory=dict)
    stag: Dict[str, dict] = field(default_factory=dict)
    splc: Dict[str, dict] = field(default_factory=dict)
    swind: Dict[str, dict] = field(default_factory=dict)
    sseis: Dict[str, dict] = field(default_factory=dict)
    spfc: Dict[str, dict] = field(default_factory=dict)
    posl: Dict[str, dict] = field(default_factory=dict)
    lcom: Dict[str, dict] = field(default_factory=dict)

    unavailable: List = field(default_factory=list)
    wl_node_ids: Set[int] = field(default_factory=set)
    wl_elem_ids: Set[int] = field(default_factory=set)
    inactive_elem_ids: Set[int] = field(default_factory=set)

    def has_plates(self) -> bool:
        return any(str(e.get("TYPE", "")).upper() in PLATE_TYPES
                   for e in self.elems.values())

    def has_stories(self) -> bool:
        return bool(self.stor)

    def has_cs(self) -> bool:
        return bool(self.stag)

    def node_xyz(self, nid):
        n = self.nodes.get(str(nid))
        if not n:
            return None
        return (float(n.get("X", 0.0)), float(n.get("Y", 0.0)), float(n.get("Z", 0.0)))

    def elem_nodes(self, e: dict) -> List[int]:
        raw = e.get("NODE", [])
        if isinstance(raw, list):
            return [int(x) for x in raw if x not in (0, "0", None)]
        return []

    def is_wl_node(self, nid) -> bool:
        return int(nid) in self.wl_node_ids

    def is_wl_elem(self, eid) -> bool:
        return int(eid) in self.wl_elem_ids


def _norm_nodes(raw: Dict[str, dict], f: float) -> Dict[str, dict]:
    out = {}
    for nid, n in raw.items():
        out[str(nid)] = {
            "X": float(n.get("X", 0.0)) * f,
            "Y": float(n.get("Y", 0.0)) * f,
            "Z": float(n.get("Z", 0.0)) * f,
        }
    return out


def _build_whitelist(ctx: "ScanContext"):
    cfg = ctx.cfg
    wl_groups = set(cfg.wl_element_groups)
    for g in ctx.grup.values():
        name = g.get("NAME", "")
        if name in wl_groups or cfg.name_whitelisted(name):
            for nid in g.get("N_LIST", []) or []:
                ctx.wl_node_ids.add(int(nid))
            for eid in g.get("E_LIST", []) or []:
                ctx.wl_elem_ids.add(int(eid))


def _build_inactive_elems(ctx: "ScanContext"):
    if not ctx.stag:
        return
    grp_elems = {}
    for g in ctx.grup.values():
        grp_elems[g.get("NAME", "")] = set(int(x) for x in (g.get("E_LIST", []) or []))
    activated, deactivated = set(), set()
    for sid in sorted(ctx.stag, key=lambda s: _to_int(s, 0)):
        st = ctx.stag[sid]
        for a in st.get("ACT_ELEM", []) or []:
            activated |= grp_elems.get(a.get("GRUP_NAME", ""), set())
        for d in st.get("DACT_ELEM", []) or []:
            deactivated |= grp_elems.get(d.get("GRUP_NAME", ""), set())
    all_e = set(int(e) for e in ctx.elems)
    if activated:
        ctx.inactive_elem_ids = (all_e - activated) | (deactivated - activated)
    else:
        ctx.inactive_elem_ids = deactivated


def collect(client: ReadOnlyClient, cfg: ScanConfig, log=print) -> "ScanContext":
    ctx = ScanContext(cfg=cfg)
    ctx.unit_raw = client.smoke()
    dist = str(ctx.unit_raw.get("DIST", "M")).upper()
    force = str(ctx.unit_raw.get("FORCE", "KN")).upper()
    ctx.dist_factor = _DIST_TO_M.get(dist, 1.0)
    ctx.force_factor = _FORCE_TO_KN.get(force, 1.0)
    log(f"[unit] 모델 원단위 FORCE={force} DIST={dist} → 정규화 kN, m "
        f"(dist x {ctx.dist_factor}, force x {ctx.force_factor})")

    for attr, key in COLLECTIONS.items():
        try:
            data = client.get_collection(key)
        except ResourceUnavailable as e:
            ctx.unavailable.append((key, e.status))
            log(f"[warn] db/{key} 조회 실패(status={e.status}) — 의존 점검은 '미조회'")
            data = {}
        setattr(ctx, attr, data)

    for lk in LCOM_KEYS:
        try:
            ctx.lcom[lk] = client.get_collection(lk)
        except ResourceUnavailable as e:
            ctx.unavailable.append((lk, e.status))
            ctx.lcom[lk] = {}

    ctx.nodes = _norm_nodes(ctx.nodes, ctx.dist_factor)
    _build_whitelist(ctx)
    _build_inactive_elems(ctx)
    return ctx


def run_checks(ctx: "ScanContext", log=print) -> List[Finding]:
    load_all_checks()
    findings: List[Finding] = []
    disabled = set(ctx.cfg.disabled_checks)
    for cid in sorted(CHECK_REGISTRY):
        name, fn = CHECK_REGISTRY[cid]
        if cid in disabled:
            log(f"[skip] {cid} {name} (disabled_checks)")
            continue
        try:
            res = fn(ctx) or []
        except Exception as e:
            log(f"[error] 체크 {cid} 예외: {type(e).__name__}: {e}")
            res = [Finding(cid, name, SEVERITY_INFO, "MODEL",
                           description=f"체크 실행 중 예외: {e}",
                           recommendation="스캐너 이슈로 보고")]
        _mark_whitelist(ctx, res)
        findings.extend(res)
        log(f"[check] {cid} {name}: {len(res)}건")

    for key, status in ctx.unavailable:
        findings.append(Finding(
            f"EP-{key}", f"리소스 미조회: db/{key}", SEVERITY_INFO, "MODEL",
            description=f"db/{key} GET 실패(status={status}). 이 리소스에 의존하는 점검은 생략됨.",
            recommendation="엔드포인트 미지원이거나 일시적 실패. 라이브 환경에서 재확인."))
    findings.sort(key=lambda f: f.sort_key())
    return findings


def _mark_whitelist(ctx: "ScanContext", findings: List[Finding]):
    for f in findings:
        if not f.target_ids:
            continue
        if f.target_type == "NODE" and all(ctx.is_wl_node(i) for i in f.target_ids):
            f.whitelisted = True
        elif f.target_type in ("ELEM", "PLATE") and all(ctx.is_wl_elem(i) for i in f.target_ids):
            f.whitelisted = True
