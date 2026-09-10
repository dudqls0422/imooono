"""생성 결과 자료구조.

``geometry.build_model`` 이 만들고, ``writer.write_model`` 이 ``{"Assign": ...}``
바디로 직렬화하며, ``cli`` 가 요약을 출력한다. ``node_assign`` / ``elem_assign``
은 원본 이식 함수가 채운 딕셔너리를 그대로 담는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class WarehouseModel:
    node_assign: Dict[str, dict] = field(default_factory=dict)   # id -> {X,Y,Z}
    elem_assign: Dict[str, dict] = field(default_factory=dict)   # id -> {TYPE,...}
    next_node_id: int = 1
    next_elem_id: int = 1
    counts: Dict[str, int] = field(default_factory=dict)
    meta: Dict = field(default_factory=dict)

    def node_count(self) -> int:
        return len(self.node_assign)

    def elem_count(self) -> int:
        return len(self.elem_assign)
