"""점검 항목 레지스트리 + Finding 자료구조.

각 체크 함수 시그니처: ``def check(ctx: ScanContext) -> list[Finding]``.
새 체크는 해당 모듈에서 정의하고 이 파일의 CHECK_REGISTRY 에 등록한다(id 순서 = 리포트 정렬).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List

SEVERITY_ERROR = "오류"
SEVERITY_WARN = "경고"
SEVERITY_INFO = "정보"
SEVERITY_ORDER = {SEVERITY_ERROR: 0, SEVERITY_WARN: 1, SEVERITY_INFO: 2}

TARGET_TYPES = ("NODE", "ELEM", "PLATE", "LOADCASE", "COMBO", "MODEL")


@dataclass
class Finding:
    check_id: str
    check_name: str
    severity: str                       # SEVERITY_ERROR / WARN / INFO
    target_type: str                    # TARGET_TYPES 중 하나
    target_ids: List = field(default_factory=list)
    description: str = ""
    recommendation: str = ""
    whitelisted: bool = False

    def sort_key(self):
        return (SEVERITY_ORDER.get(self.severity, 9), self.check_id)


# check_id -> (이름, 함수).
CHECK_REGISTRY: "dict[str, tuple[str, Callable]]" = {}


def register(check_id: str, name: str):
    def deco(fn):
        CHECK_REGISTRY[check_id] = (name, fn)
        return fn
    return deco


def load_all_checks():
    """checks 하위 모듈을 모두 import 해 레지스트리를 채운다."""
    from . import geometry, properties, boundary, connectivity, loads, mesh, combos  # noqa: F401
    return CHECK_REGISTRY
