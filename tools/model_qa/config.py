"""스캐너 설정: 허용오차/임계값 기본값 + ``--config`` TOML 로드.

TOML 예시::

    [tolerances]
    tol_merge_mm = 1.0
    tol_zero_mm  = 1.0
    aspect_warn  = 4
    aspect_err   = 10

    [whitelist]
    element_groups = ["DUMMY_GRP", "REF_GRP"]
    name_patterns  = ["DUMMY_*", "REF_*"]
    disabled_checks = ["G7"]

CLI 인자가 있으면 CLI 값이 TOML 값을 덮어쓴다.
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import List

try:  # py311+
    import tomllib as _toml
except ModuleNotFoundError:  # pragma: no cover
    import tomli as _toml  # type: ignore


@dataclass
class ScanConfig:
    # 허용오차 (사용자 표기는 mm, 내부 계산은 m)
    tol_merge_mm: float = 1.0
    tol_zero_mm: float = 1.0
    aspect_warn: float = 4.0
    aspect_err: float = 10.0
    overlap_min_mm: float = 10.0
    collinear_deg: float = 1.0

    # 화이트리스트
    wl_element_groups: List[str] = field(default_factory=list)
    wl_name_patterns: List[str] = field(default_factory=list)
    disabled_checks: List[str] = field(default_factory=list)

    @property
    def tol_merge_m(self) -> float:
        return self.tol_merge_mm / 1000.0

    @property
    def tol_zero_m(self) -> float:
        return self.tol_zero_mm / 1000.0

    @property
    def overlap_min_m(self) -> float:
        return self.overlap_min_mm / 1000.0

    def name_whitelisted(self, name) -> bool:
        if not name:
            return False
        return any(fnmatch.fnmatch(name, pat) for pat in self.wl_name_patterns)


def load_config(path=None) -> "ScanConfig":
    cfg = ScanConfig()
    if not path:
        return cfg
    with open(path, "rb") as fh:
        data = _toml.load(fh)
    tol = data.get("tolerances", {})
    for k in ("tol_merge_mm", "tol_zero_mm", "aspect_warn", "aspect_err",
              "overlap_min_mm", "collinear_deg"):
        if k in tol:
            setattr(cfg, k, float(tol[k]))
    wl = data.get("whitelist", {})
    cfg.wl_element_groups = list(wl.get("element_groups", []))
    cfg.wl_name_patterns = list(wl.get("name_patterns", []))
    cfg.disabled_checks = list(wl.get("disabled_checks", []))
    return cfg


def apply_cli_overrides(cfg: "ScanConfig", args) -> "ScanConfig":
    if getattr(args, "tol_merge", None) is not None:
        cfg.tol_merge_mm = float(args.tol_merge)
    if getattr(args, "tol_zero", None) is not None:
        cfg.tol_zero_mm = float(args.tol_zero)
    if getattr(args, "aspect_warn", None) is not None:
        cfg.aspect_warn = float(args.aspect_warn)
    if getattr(args, "aspect_err", None) is not None:
        cfg.aspect_err = float(args.aspect_err)
    return cfg
