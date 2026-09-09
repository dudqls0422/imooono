"""읽기/쓰기 클라이언트 + 빈 모델 가드 + matl/sect 존재 확인 + 순서 PUT.

portal_frame_gen.writer 에서 client / empty_model_guard / put_unit /
_is_success·_error_text·_looks_unsupported 를 **복사**해 warehouse 용으로
사용한다(공용 midas_common 추출은 두 도구 모두 라이브 검증된 뒤 후속).

라이브 쓰기 미검증: catalog 스키마 기반, 실제 PUT 왕복 미확인.
쓰기 순서(portal 일관): GET 전제조건(빈 모델 가드 + matl/sect 존재) →
PUT db/UNIT(첫 쓰기·verb 프로브) → PUT db/NODE → PUT db/ELEM.
UNIT 은 모델 단위를 덮어쓰지만, 그 앞에서 가드가 빈 모델임을 확인했으므로
허용된다(portal PR #9 QA 반려 반영 — 가드는 어떤 PUT 보다 먼저).
"""
from __future__ import annotations

from typing import Callable, Dict, List

import requests

from .model import WarehouseModel

DEFAULT_BASE_URL = "https://moa-engineers.midasit.com:443/gen"
UNIT_BODY = {"Assign": {"1": {"FORCE": "KN", "DIST": "M",
                              "HEAT": "KCAL", "TEMPER": "C"}}}


class LiveWriteUnsupported(Exception):
    """PUT db/UNIT 이 405/401/403/'not supported' — 라이브 쓰기 불가 가능성."""


class ModelNotEmpty(Exception):
    """빈 모델 가드 실패 — 이미 노드/요소가 있음."""


class MatlSectMissing(Exception):
    """matl/sect id 가 현재 모델에 없음."""

    def __init__(self, missing_matl, missing_sect):
        self.missing_matl = missing_matl
        self.missing_sect = missing_sect
        parts = []
        if missing_matl is not None:
            parts.append(f"MATL id {missing_matl}")
        if missing_sect is not None:
            parts.append(f"SECT id {missing_sect}")
        super().__init__("현재 모델에 없는 id — " + ", ".join(parts)
                         + ". MIDAS 에서 먼저 정의 후 재실행.")


class WriteFailed(Exception):
    """벌크 쓰기 중 실패. 그때까지 성공한 단계 목록을 담는다."""

    def __init__(self, step: str, detail: str, done: List[str]):
        self.step = step
        self.detail = detail
        self.done = done
        super().__init__(f"[{step}] 쓰기 실패: {detail} | 성공한 단계: "
                         + (", ".join(done) if done else "없음"))


# --------------------------------------------------------------------------
# 클라이언트 (portal 복사)
# --------------------------------------------------------------------------
class WarehouseClient:
    """GET / PUT 만. POST/DELETE 없음. 모든 요청을 request_log 에 기록."""

    def __init__(self, mapi_key: str, base_url: str = DEFAULT_BASE_URL,
                 timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._s = requests.Session()
        self._s.headers.update({"MAPI-Key": mapi_key,
                                "Content-Type": "application/json"})
        self.request_log: List[tuple] = []

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def get(self, path: str):
        url = self._url(path)
        try:
            r = self._s.get(url, timeout=self.timeout)
        except (requests.ConnectionError, requests.Timeout):
            self.request_log.append(("GET", url, "ERR"))
            raise
        self.request_log.append(("GET", url, r.status_code))
        return _json_or_none(r)

    def put(self, path: str, body: dict):
        url = self._url(path)
        r = self._s.put(url, json=body, timeout=self.timeout)
        self.request_log.append(("PUT", url, r.status_code))
        return r

    def verbs_used(self) -> List[str]:
        return sorted({v for v, _u, _s in self.request_log})


def _json_or_none(resp):
    try:
        return resp.json()
    except ValueError:
        return None


# --------------------------------------------------------------------------
# 응답 파싱 (portal 복사 — 명시적 성공 형태 요구)
# --------------------------------------------------------------------------
def _is_success(resp, expect_key: str = None) -> bool:
    if resp.status_code // 100 != 2:
        return False
    body = _json_or_none(resp)
    if body is None or body == "" or body == {}:
        return True
    if not isinstance(body, dict):
        return True
    if "error" in body:
        return False
    if expect_key and expect_key in body:
        return True
    if "Assign" in body:
        return True
    return "message" not in body


def _error_text(resp) -> str:
    body = _json_or_none(resp)
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            return f"{err.get('code', '')} {err.get('message', '')}".strip()
        if "message" in body:
            return str(body["message"])
    return f"HTTP {resp.status_code}: {str(resp.text)[:200]}"


def _looks_unsupported(resp) -> bool:
    if resp.status_code in (401, 403, 405):
        return True
    txt = (str(resp.text) or "").lower()
    return "not supported" in txt or "method not allowed" in txt


def _count_collection(body, key) -> int:
    if not isinstance(body, dict):
        return 0
    if "message" in body and not body.get(key):
        return 0
    inner = body.get(key)
    return len(inner) if isinstance(inner, dict) else 0


def _collection_keys(body, key):
    if not isinstance(body, dict):
        return set()
    if "message" in body and not body.get(key):
        return set()
    inner = body.get(key)
    return set(inner.keys()) if isinstance(inner, dict) else set()


# --------------------------------------------------------------------------
# 전제조건 (GET 만) — 첫 쓰기 전에 통과해야 함
# --------------------------------------------------------------------------
def empty_model_guard(client, force: bool = False, log: Callable = print):
    """GET db/NODE + db/ELEM. 데이터가 있으면 중단(force 면 요란한 경고)."""
    node_n = _count_collection(client.get("db/NODE"), "NODE")
    elem_n = _count_collection(client.get("db/ELEM"), "ELEM")
    if node_n or elem_n:
        msg = (f"빈 모델이 아님 — 기존 절점 {node_n}개 / 요소 {elem_n}개. "
               "창고 프레임 생성기는 빈 모델에서만 실행.")
        if not force:
            raise ModelNotEmpty(msg)
        log("!" * 60)
        log(f"[강제 진행] {msg}")
        log("[강제 진행] --force 지정 — 기존 모델 위에 겹쳐 쓰기 시도. 위험.")
        log("!" * 60)


def check_matl_sect(client, matl: int, sect: int, log: Callable = print):
    """GET db/MATL + db/SECT → str(matl)·str(sect) 가 키에 있는지. 없으면 중단."""
    matl_keys = _collection_keys(client.get("db/MATL"), "MATL")
    sect_keys = _collection_keys(client.get("db/SECT"), "SECT")
    missing_m = None if str(matl) in matl_keys else matl
    missing_s = None if str(sect) in sect_keys else sect
    if missing_m is not None or missing_s is not None:
        raise MatlSectMissing(missing_m, missing_s)


def id_overlap_warning(client, model: WarehouseModel, log: Callable = print):
    """--force + 비어있지 않은 모델: 시작번호 구간이 기존 id 와 겹치면 경고(중단 아님)."""
    nkeys = _collection_keys(client.get("db/NODE"), "NODE")
    ekeys = _collection_keys(client.get("db/ELEM"), "ELEM")
    for label, keys, start, end in (
        ("절점", nkeys, model.meta["node_start"], model.next_node_id),
        ("요소", ekeys, model.meta["elem_start"], model.next_elem_id),
    ):
        nums = {int(k) for k in keys if str(k).lstrip("-").isdigit()}
        clash = sorted(n for n in nums if start <= n < end)
        if clash:
            log(f"[경고] {label} 시작번호 구간 [{start}, {end}) 이(가) 기존 "
                f"{label} id {clash[:10]}{' …' if len(clash) > 10 else ''} 와 겹침 — "
                "덮어쓰기됨")


# --------------------------------------------------------------------------
# 쓰기
# --------------------------------------------------------------------------
def put_unit(client, log: Callable = print) -> None:
    resp = client.put("db/UNIT", UNIT_BODY)
    if _looks_unsupported(resp):
        raise LiveWriteUnsupported(
            f"PUT db/UNIT → HTTP {resp.status_code}. 라이브 쓰기 미지원 가능성 — "
            "Main 보고 필요.")
    if not _is_success(resp, "UNIT"):
        raise WriteFailed("UNIT", _error_text(resp), [])
    log("[write] db/UNIT (kN, m) 설정")


def write_model(client, model: WarehouseModel, log: Callable = print) -> Dict:
    """PUT db/NODE 벌크 → PUT db/ELEM 벌크. 첫 실패에서 WriteFailed."""
    done: List[str] = []

    resp = client.put("db/NODE", {"Assign": model.node_assign})
    if not _is_success(resp, "NODE"):
        raise WriteFailed("NODE", _error_text(resp), list(done))
    done.append("NODE")
    ns = model.meta["node_start"]
    log(f"[write] db/NODE {model.node_count()}개 (id {ns}..{model.next_node_id - 1})")

    resp = client.put("db/ELEM", {"Assign": model.elem_assign})
    if not _is_success(resp, "ELEM"):
        raise WriteFailed("ELEM", _error_text(resp), list(done))
    done.append("ELEM")
    es = model.meta["elem_start"]
    log(f"[write] db/ELEM {model.elem_count()}개 (id {es}..{model.next_elem_id - 1})")

    return {"done": done, "counts": model.counts}
