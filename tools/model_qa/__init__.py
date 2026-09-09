"""MIDAS Gen NX 모델 QA 스캐너 (read-only).

현재 MIDAS 에 열린 모델을 GET 전용으로 조회해 지오메트리/물성/경계/연결/하중/메시/조합
정합성을 점검하고, 풍/지진 적용조건을 추출해 openpyxl 3시트 리포트로 출력한다.

엔트리: ``python -m tools.model_qa --mapi-key <KEY> --out report.xlsx``
"""

__version__ = "0.1.0"
