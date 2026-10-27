"""``python -m tools.cad_training`` 진입점.

흐름: manifest 의 6개 파일 생성(R2018 DXF) → [--no-preview 가 아니면] 시트별 PNG.
네트워크·MIDAS 연동 없음.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .build import build_all

EXIT_OK = 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m tools.cad_training",
        description="AutoCAD 기본 명령어 교육자료(DXF) 생성기 — M1 그리기 / M2 수정 / C1 종합실습")
    p.add_argument("--out", default="output/cad_training", help="출력 폴더 (기본: output/cad_training)")
    p.add_argument("--no-preview", action="store_true", help="시트별 PNG 미리보기 생략")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    written = build_all(Path(args.out), preview=not args.no_preview)
    dxf = [p for p in written if p.suffix == ".dxf"]
    png = [p for p in written if p.suffix == ".png"]
    for p in dxf:
        print(f"생성: {p}")
    if png:
        print(f"미리보기 PNG {len(png)}장: {Path(args.out) / 'preview'}")
    return EXIT_OK
