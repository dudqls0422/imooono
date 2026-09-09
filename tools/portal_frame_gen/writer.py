"""읽기/쓰기 클라이언트 + 빈 모델 가드 + 순서대로 PUT.

라이브 쓰기 미검증: 이 모듈은 ``midas-api`` catalog 스키마 기반이며 실제
MIDAS 쓰기 왕복은 확인되지 않았다. ``db/SWIND`` 전례처럼 catalog ↔ 라이브
불일치 가능. 응답은 성공·에러 두 형태를 방어적으로 파싱하고, 첫 실패에서
중단하며 그때까지 성공한 단계/ID 범위를 보고한다.

쓰기 순서: PUT db/UNIT → (해석·가드는 CLI) → PUT db/NODE → db/ELEM →
db/CONS → db/GRUP.
"""
from __future__ import annotations

from typing import Callable, Dict, List

import requests

from .model import KIND_COLUMN, KIND_EAVE_STRUT, KIND_RAFTER, PortalFrameModel

DEFAULT_BASE_URL = "https://moa-engineers.midasit.com:443/gen"
UNIT_BODY = {"Assign": {"1": {"FORCE": "KN", "DIST": "M",
                              "HEAT": "KCAL", "TEMPER": "C"}}}
# db/CONS.GROUP_NAME 미지정("") 허용 여부는 라이브 미검증(write-recon.md §8).
# 거부되면 사용자가 경계그룹을 먼저 만들거나 코드에서 기본값을 넣어야 한다.
DEFAULT_BOUNDARY_GROUP = ""


class LiveWriteUnsupported(Exception):
    """PUT db/UNIT 이 405/401/403/'not supported' — 라이브 쓰기 불가 가능성."""


class ModelNotEmpty(Exception):
    """빈 모델 가드 실패 — 이미 노드/요소가 있음."""


class WriteFailed(Exception):
    """벌크 쓰기 중 실패. 그때까지 성공한 단계 목록을 담는다."""

    def __init__(self, step: str, detail: str, done: List[str]):
        self.step = step
        self.detail = detail
        self.done = done
        super().__init__(f"[{step}] 쓰기 실패: {detail} | 성공한 단계: "
                         + (", ".join(done) if done else "없음"))


# --------------------------------------------------------------------------
# 클라이언트
# --------------------------------------------------------------------------
class PortalFrameClient:
    """GET / PUT / DELETE 만. POST 없음. 모든 요청을 request_log 에 기록."""

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

    def delete(self, path: str):
        url = self._url(path)
        r = self._s.delete(url, timeout=self.timeout)
        self.request_log.append(("DELETE", url, r.status_code))
        return r

    def verbs_used(self) -> List[str]:
        return sorted({v for v, _u, _s in self.request_log})


def _json_or_none(resp):
    try:
        return resp.json()
    except ValueError:
        return None


# --------------------------------------------------------------------------
# 응답 파싱 (성공 / 에러 두 형태 방어적)
# --------------------------------------------------------------------------
def _is_success(resp, expect_key: str = None) -> bool:
    """쓰기 성공은 명시적 형태를 요구한다.

    2xx 라도 MIDAS 가 200 + ``{"message": "Invalid..."}`` 로 실패를 돌려줄 수
    있으므로, 성공은 (a) 본문 없음, (b) 에코된 컬렉션 키(``expect_key``) 존재,
    (c) ``Assign`` 키 에코 중 하나여야 한다. ``error`` 키나 순수
    ``{"message": ...}`` 응답은 실패로 본다.
    """
    if resp.status_code // 100 != 2:
        return False
    body = _json_or_none(resp)
    if body is None or body == "" or body == {}:
        return True  # 200 무바디
    if not isinstance(body, dict):
        return True
    if "error" in body:
        return False
    if expect_key and expect_key in body:
        return True
    if "Assign" in body:
        return True
    # 컬렉션 키도 Assign 도 없이 message 만 → 실패로 간주(방어적).
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


# --------------------------------------------------------------------------
# 단계별 쓰기
# --------------------------------------------------------------------------
def put_unit(client: PortalFrameClient, log: Callable = print) -> None:
    """첫 실제 쓰기. verb 미지원이면 LiveWriteUnsupported."""
    resp = client.put("db/UNIT", UNIT_BODY)
    if _looks_unsupported(resp):
        raise LiveWriteUnsupported(
            f"PUT db/UNIT → HTTP {resp.status_code}. 라이브 쓰기 미지원 가능성 — "
            "Main 보고 필요.")
    if not _is_success(resp, "UNIT"):
        raise WriteFailed("UNIT", _error_text(resp), [])
    log("[write] db/UNIT (kN, m) 설정")


def empty_model_guard(client: PortalFrameClient, force: bool = False,
                      log: Callable = print) -> None:
    """GET db/NODE + db/ELEM. 하나라도 데이터가 있으면 중단(force 면 경고)."""
    node_n = _count_collection(client.get("db/NODE"), "NODE")
    elem_n = _count_collection(client.get("db/ELEM"), "ELEM")
    if node_n or elem_n:
        msg = (f"빈 모델이 아님 — 기존 절점 {node_n}개 / 요소 {elem_n}개. "
               "포탈 프레임 생성기는 빈 모델에서만 실행.")
        if not force:
            raise ModelNotEmpty(msg)
        log("!" * 60)
        log(f"[강제 진행] {msg}")
        log("[강제 진행] --force 지정 — 기존 모델 위에 덮어쓰기 시도. 위험.")
        log("!" * 60)
    for key, name in (("db/MATL", "MATL"), ("db/SECT", "SECT"),
                      ("db/CONS", "CONS")):
        n = _count_collection(client.get(key), name)
        if n:
            log(f"[안내] 기존 {key} {n}건 존재 — 재료/단면 사전 정의는 정상.")


def write_model(client: PortalFrameClient, model: PortalFrameModel,
                resolved, no_groups: bool = False,
                log: Callable = print) -> Dict[str, object]:
    """NODE → ELEM → CONS → GRUP 순서 PUT. 첫 실패에서 WriteFailed."""
    done: List[str] = []

    nbody = {"Assign": {str(n.id): {"X": n.x, "Y": n.y, "Z": n.z}
                        for n in model.nodes}}
    _put_step(client, "db/NODE", nbody, "NODE", done)
    log(f"[write] db/NODE {len(model.nodes)}개 (id 1..{len(model.nodes)})")

    ebody = {"Assign": {}}
    for e in model.elements:
        sid = resolved.section_ids[e.section_name]
        ebody["Assign"][str(e.id)] = {
            "TYPE": "BEAM", "MATL": resolved.material_id, "SECT": sid,
            "NODE": [e.n1, e.n2], "ANGLE": e.beta_angle,
        }
    _put_step(client, "db/ELEM", ebody, "ELEM", done)
    log(f"[write] db/ELEM {len(model.elements)}개 "
        f"(기둥 {len(model.elems_by_kind(KIND_COLUMN))} / "
        f"rafter {len(model.elems_by_kind(KIND_RAFTER))} / "
        f"스트럿 {len(model.elems_by_kind(KIND_EAVE_STRUT))})")

    cbody = {"Assign": {}}
    for s in model.supports:
        cbody["Assign"][str(s.node_id)] = {"ITEMS": [{
            "ID": s.node_id, "GROUP_NAME": DEFAULT_BOUNDARY_GROUP,
            "CONSTRAINT": s.constraint,
        }]}
    _put_step(client, "db/CONS", cbody, "CONS", done)
    log(f"[write] db/CONS {len(model.supports)}개 지점 "
        f"(구속 {model.supports[0].constraint if model.supports else '-'})")

    if not no_groups and model.groups:
        gbody = {"Assign": {}}
        for i, g in enumerate(model.groups, start=1):
            gbody["Assign"][str(i)] = {"NAME": g.name, "P_TYPE": 0,
                                       "N_LIST": [], "E_LIST": list(g.elem_ids)}
        _put_step(client, "db/GRUP", gbody, "GRUP", done)
        log(f"[write] db/GRUP {len(model.groups)}개 "
            f"({', '.join(g.name for g in model.groups)})")

    return {"done": done, "counts": model.counts()}


def _put_step(client, path, body, step, done):
    resp = client.put(path, body)
    expect_key = path.rsplit("/", 1)[-1]  # NODE / ELEM / CONS / GRUP
    if not _is_success(resp, expect_key):
        raise WriteFailed(step, _error_text(resp), list(done))
    done.append(step)


def _count_collection(body, key) -> int:
    if not isinstance(body, dict):
        return 0
    if "message" in body and not body.get(key):
        return 0
    inner = body.get(key)
    return len(inner) if isinstance(inner, dict) else 0


# --------------------------------------------------------------------------
# 조건부 롤백 (DELETE 지원 시만)
# --------------------------------------------------------------------------
def rollback(client: PortalFrameClient, model: PortalFrameModel,
             log: Callable = print) -> bool:
    """역순(CONS→ELEM→NODE) DELETE 시도. 지원 안 되면 False + 안내."""
    ok = True
    for path, ids in (
        ("db/CONS", [s.node_id for s in model.supports]),
        ("db/ELEM", [e.id for e in model.elements]),
        ("db/NODE", [n.id for n in model.nodes]),
    ):
        if not ids:
            continue
        idlist = ",".join(str(i) for i in ids)
        resp = client.delete(f"{path}/{idlist}")
        if _looks_unsupported(resp) or not _is_success(resp):
            ok = False
            log(f"[rollback] {path} DELETE 미지원/실패 (HTTP {resp.status_code}).")
            break
        log(f"[rollback] {path} {len(ids)}건 삭제")
    if not ok:
        log("[rollback] 자동 롤백 불가 — MIDAS 에서 새 빈 모델을 열고 재실행 권장.")
        log(f"[rollback] 생성 시도분: 노드 {len(model.nodes)} / "
            f"요소 {len(model.elements)} / 지점 {len(model.supports)}")
    return ok
