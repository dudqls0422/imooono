"""엔트리 CLI.

``python -m tools.model_qa --mapi-key <KEY> --out report.xlsx``

종료코드: 0 정상(리포트 생성, findings 유무 무관) / 2 환경·인자 오류(스모크 실패 포함)
          / 3 리포트 쓰기 실패
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

from .checks import CHECK_REGISTRY, load_all_checks
from .client import DEFAULT_BASE_URL, BaseUrlUnreachable, ReadOnlyClient
from .config import apply_cli_overrides, load_config
from .loadcond import extract_seismic, extract_wind
from .report import write_report
from .scan import collect, run_checks

EXIT_OK = 0
EXIT_ENV = 2
EXIT_WRITE = 3


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m tools.model_qa",
        description="MIDAS Gen NX 모델 QA 스캐너 (read-only). 현재 열린 모델을 점검한다.")
    p.add_argument("--mapi-key", default=None, help="MAPI-Key. 없으면 환경변수 MAPI_KEY 사용.")
    p.add_argument("--out", default="model_qa_report.xlsx", help="리포트 xlsx 경로.")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p.add_argument("--tol-merge", type=float, default=None, help="중복 절점 허용거리(mm).")
    p.add_argument("--tol-zero", type=float, default=None, help="영길이 부재 판정(mm).")
    p.add_argument("--aspect-warn", type=float, default=None, help="판 종횡비 경고.")
    p.add_argument("--aspect-err", type=float, default=None, help="판 종횡비 오류.")
    p.add_argument("--config", default=None, help="TOML 설정(허용오차/화이트리스트).")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    key = args.mapi_key or os.environ.get("MAPI_KEY")
    if not key:
        build_parser().print_usage(sys.stderr)
        print("오류: --mapi-key 또는 환경변수 MAPI_KEY 필요.", file=sys.stderr)
        return EXIT_ENV

    try:
        cfg = load_config(args.config)
    except Exception as e:
        print(f"오류: --config 로드 실패: {e}", file=sys.stderr)
        return EXIT_ENV
    cfg = apply_cli_overrides(cfg, args)

    load_all_checks()
    n_checks = len([c for c in CHECK_REGISTRY if c not in set(cfg.disabled_checks)])

    client = ReadOnlyClient(key, base_url=args.base_url)
    print(f"[scan] base_url={args.base_url}")
    try:
        ctx = collect(client, cfg, log=lambda m: print(m))
    except BaseUrlUnreachable as e:
        print(f"[환경 블로커] {e}", file=sys.stderr)
        print("MIDAS 실행·모델 오픈·mapi_key 확인 후 재시도.", file=sys.stderr)
        return EXIT_ENV

    findings = run_checks(ctx, log=lambda m: print(m))
    wind_rows = extract_wind(ctx)
    seis_rows = extract_seismic(ctx)

    meta = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "base_url": args.base_url,
        "n_checks": n_checks,
    }
    try:
        write_report(args.out, findings, ctx, wind_rows, seis_rows, meta)
    except Exception as e:
        print(f"[리포트 쓰기 실패] {e}", file=sys.stderr)
        return EXIT_WRITE

    n_err = sum(1 for f in findings if f.severity == "오류" and not f.whitelisted)
    n_warn = sum(1 for f in findings if f.severity == "경고" and not f.whitelisted)
    n_info = sum(1 for f in findings if f.severity == "정보" and not f.whitelisted)
    n_wl = sum(1 for f in findings if f.whitelisted)
    print(f"[완료] 리포트: {args.out}  (오류 {n_err} / 경고 {n_warn} / 정보 {n_info}, "
          f"화이트리스트 {n_wl})")
    verbs = sorted({m for m, _u, _s in client.request_log})
    print(f"[read-only] 요청 {len(client.request_log)}건, verb={verbs}")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
