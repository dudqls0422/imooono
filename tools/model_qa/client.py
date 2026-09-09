"""MIDAS Gen NX read-only HTTP 클라이언트.

- GET 전용. ``post``/``put``/``delete`` 는 정의하지 않으며, 호출 시 ``RuntimeError``.
- ``/doc/open``, ``/doc/save`` 등 mutating 경로는 절대 호출하지 않는다. 현재 MIDAS 에 열린 모델 대상.
- 응답 봉투 ``{"KEY": {"1": {...}}}`` 에서 내부 dict 를 언랩한다.
- 빈 컬렉션은 HTTP 200 + ``{"message": ""}`` (데이터 키 없음) 로 오며, 이는 오류가 아니라 빈 dict.
"""
from __future__ import annotations

import time
from typing import Any, Dict

import requests

DEFAULT_BASE_URL = "https://moa-engineers.midasit.com:443/gen"
TIMEOUT = 30


class ResourceUnavailable(Exception):
    """리소스 조회 실패(엔드포인트 미지원 / non-200 / 도달 불가). 스캔은 계속한다."""

    def __init__(self, key, status, detail=""):
        self.key = key
        self.status = status
        self.detail = detail
        super().__init__(f"{key}: status={status} {detail}".strip())


class BaseUrlUnreachable(Exception):
    """base_url 자체 도달 불가 → CLI exit 2."""


class ReadOnlyClient:
    def __init__(self, mapi_key, base_url=DEFAULT_BASE_URL, timeout=TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._s = requests.Session()
        self._s.headers.update({
            "MAPI-Key": mapi_key,
            "Content-Type": "application/json",
        })
        self.request_log = []   # (method, url, status) — read-only 증명용

    # ---- 금지된 verb ----
    def post(self, *a, **k):
        raise RuntimeError("ReadOnlyClient: POST 금지")

    def put(self, *a, **k):
        raise RuntimeError("ReadOnlyClient: PUT 금지")

    def delete(self, *a, **k):
        raise RuntimeError("ReadOnlyClient: DELETE 금지")

    # ---- GET ----
    def _get(self, path):
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_exc = None
        for attempt in range(2):   # 최초 + 재시도 1회 (네트워크 오류만)
            try:
                resp = self._s.get(url, timeout=self.timeout)
                self.request_log.append(("GET", url, resp.status_code))
                return resp
            except (requests.ConnectionError, requests.Timeout) as e:
                last_exc = e
                if attempt == 0:
                    time.sleep(0.5)
                    continue
        self.request_log.append(("GET", url, "NETERR"))
        raise BaseUrlUnreachable(f"{url}: {last_exc}")

    def get_raw(self, path) -> Dict[str, Any]:
        """경로를 그대로 GET 해 JSON 전체 반환(봉투 언랩 안 함)."""
        resp = self._get(path)
        if resp.status_code != 200:
            raise ResourceUnavailable(path, resp.status_code, resp.text[:200])
        try:
            return resp.json()
        except ValueError:
            raise ResourceUnavailable(path, 200, "JSON 파싱 실패")

    def get_collection(self, key) -> Dict[str, Any]:
        """``GET {base}/db/{KEY}`` → ``{"KEY": {...}}`` 언랩. 빈 컬렉션이면 ``{}``.

        non-200 또는 도달 불가면 ``ResourceUnavailable``.
        """
        resp = self._get(f"db/{key}")
        if resp.status_code != 200:
            raise ResourceUnavailable(key, resp.status_code, resp.text[:200])
        try:
            body = resp.json()
        except ValueError:
            raise ResourceUnavailable(key, 200, "JSON 파싱 실패")
        if not isinstance(body, dict):
            raise ResourceUnavailable(key, 200, "예상치 못한 응답 형식")
        if key in body and isinstance(body[key], dict):
            return body[key]
        if "message" in body:      # {"message": ""} = 빈 컬렉션
            return {}
        return {}

    def smoke(self) -> Dict[str, str]:
        """``db/UNIT`` GET. 실패하면 예외(호출부에서 exit 2)."""
        try:
            unit = self.get_collection("UNIT")
        except (ResourceUnavailable, BaseUrlUnreachable) as e:
            raise BaseUrlUnreachable(
                "db/UNIT 스모크 실패 — MIDAS 실행·모델 오픈·mapi_key 확인. "
                f"({e})"
            )
        for _id, row in unit.items():
            if isinstance(row, dict) and "DIST" in row:
                return row
        raise BaseUrlUnreachable("db/UNIT 응답에 단위 정보 없음 — MIDAS 상태 확인")
