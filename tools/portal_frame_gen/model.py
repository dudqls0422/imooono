"""계산 모델 자료구조 (dataclass).

``geometry.build_model`` 이 생성하고, ``writer`` 가 PUT 바디로 직렬화하며,
``verify`` 가 라이브 GET 결과와 대조한다. 좌표계: X=스팬방향, Y=길이방향,
Z=수직 상향. 길이 단위는 m (모델 단위는 항상 kN·m 로 PUT).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

# 부재 종류
KIND_COLUMN = "column"
KIND_RAFTER = "rafter"
KIND_EAVE_STRUT = "eave_strut"

# 지점 구속 문자열 (7자리: DX DY DZ RX RY RZ RW)
CONSTRAINT_PINNED = "1110000"
CONSTRAINT_FIXED = "1111110"

# rafter(경사부재) 베타각. MIDAS 경사부재 베타각 규약이 라이브 미검증이라
# 0 으로 둔다. 강축 면내 배치 의도는 write-recon.md §8 에 한계로 기록됨.
RAFTER_BETA_ANGLE = 0.0


@dataclass
class Node:
    id: int
    x: float
    y: float
    z: float

    def xyz(self):
        return (self.x, self.y, self.z)


@dataclass
class Element:
    id: int
    kind: str            # KIND_COLUMN / KIND_RAFTER / KIND_EAVE_STRUT
    n1: int
    n2: int
    section_name: str    # 템플릿 단면명 (resolver 가 id 로 해석)
    beta_angle: float = 0.0


@dataclass
class Support:
    node_id: int
    constraint: str      # CONSTRAINT_PINNED / CONSTRAINT_FIXED


@dataclass
class Group:
    name: str
    elem_ids: List[int] = field(default_factory=list)


@dataclass
class PortalFrameModel:
    nodes: List[Node] = field(default_factory=list)
    elements: List[Element] = field(default_factory=list)
    supports: List[Support] = field(default_factory=list)
    groups: List[Group] = field(default_factory=list)
    meta: Dict = field(default_factory=dict)

    # --- 편의 조회 -------------------------------------------------------
    def elems_by_kind(self, kind: str) -> List[Element]:
        return [e for e in self.elements if e.kind == kind]

    def section_names(self) -> List[str]:
        """모델이 참조하는 단면명 (중복 제거, 등장 순서 유지)."""
        seen, out = set(), []
        for e in self.elements:
            if e.section_name not in seen:
                seen.add(e.section_name)
                out.append(e.section_name)
        return out

    def counts(self) -> Dict[str, int]:
        return {
            "nodes": len(self.nodes),
            "elements": len(self.elements),
            "columns": len(self.elems_by_kind(KIND_COLUMN)),
            "rafters": len(self.elems_by_kind(KIND_RAFTER)),
            "eave_struts": len(self.elems_by_kind(KIND_EAVE_STRUT)),
            "supports": len(self.supports),
            "groups": len(self.groups),
        }
