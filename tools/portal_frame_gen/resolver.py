"""템플릿의 재료명·단면명 → 현재 모델의 기존 ``db/MATL`` / ``db/SECT`` id.

이 도구는 재료·단면을 **만들지 않는다**(사전 정의 요구). 이름을 하나라도
못 찾으면 착수 전 중단한다 (CLI exit 5). 빈 컬렉션(``{"message": ""}``)은
"사전 정의 없음" 으로 간주.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


class NamesNotFound(Exception):
    """재료/단면 이름을 현재 모델에서 찾지 못함."""

    def __init__(self, missing_materials: List[str], missing_sections: List[str]):
        self.missing_materials = missing_materials
        self.missing_sections = missing_sections
        parts = []
        if missing_materials:
            parts.append("재료: " + ", ".join(missing_materials))
        if missing_sections:
            parts.append("단면: " + ", ".join(missing_sections))
        super().__init__("현재 모델에 없는 이름 — " + " / ".join(parts)
                         + ". MIDAS 에서 먼저 정의 후 재실행.")


@dataclass
class ResolvedIds:
    material_id: int
    section_ids: Dict[str, int]  # 단면명 -> id


def _collection(body, key):
    """GET 응답에서 컬렉션 dict 추출. 빈 컬렉션이면 {}."""
    if not isinstance(body, dict):
        return {}
    if "message" in body and not body.get(key):
        return {}
    inner = body.get(key)
    return inner if isinstance(inner, dict) else {}


def _matl_name_index(matl_coll) -> Dict[str, int]:
    """이름 -> id. 최상위 NAME 1순위, PARAM[0].DB 폴백."""
    out: Dict[str, int] = {}
    for sid, obj in matl_coll.items():
        try:
            mid = int(sid)
        except (TypeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        name = str(obj.get("NAME", "")).strip()
        if name:
            out.setdefault(name, mid)
        params = obj.get("PARAM")
        if isinstance(params, list) and params and isinstance(params[0], dict):
            db = str(params[0].get("DB", "")).strip()
            if db:
                out.setdefault(db, mid)
    return out


def _sect_name_index(sect_coll) -> Dict[str, int]:
    """이름 -> id. 최상위 SECT_NAME 1순위, SECT_BEFORE.SECT_I.SECT_NAME 폴백."""
    out: Dict[str, int] = {}
    for sid, obj in sect_coll.items():
        try:
            secid = int(sid)
        except (TypeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        name = str(obj.get("SECT_NAME", "")).strip()
        if name:
            out.setdefault(name, secid)
        before = obj.get("SECT_BEFORE")
        if isinstance(before, dict):
            si = before.get("SECT_I")
            if isinstance(si, dict):
                inner = str(si.get("SECT_NAME", "")).strip()
                if inner:
                    out.setdefault(inner, secid)
    return out


def resolve_ids(client, material_name: str,
                section_names: List[str]) -> ResolvedIds:
    """GET db/MATL, GET db/SECT 로 이름→id 해석. 실패 시 NamesNotFound."""
    matl_idx = _matl_name_index(_collection(client.get("db/MATL"), "MATL"))
    sect_idx = _sect_name_index(_collection(client.get("db/SECT"), "SECT"))

    missing_mat = [] if material_name in matl_idx else [material_name]
    wanted = []
    for n in section_names:
        if n and n not in wanted:
            wanted.append(n)
    missing_sec = [n for n in wanted if n not in sect_idx]

    if missing_mat or missing_sec:
        raise NamesNotFound(missing_mat, missing_sec)

    return ResolvedIds(
        material_id=matl_idx[material_name],
        section_ids={n: sect_idx[n] for n in wanted},
    )
