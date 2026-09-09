"""``python -m tools.warehouse_frame_gen`` 진입점.

흐름: 템플릿 읽기 → build_model(형상 조립, 네트워크 0) →
(dry-run 이면 카운트 출력 후 종료) →
빈 모델 가드(GET) → matl/sect 존재 확인(GET) → [--force 면 id 겹침 경고] →
PUT db/UNIT(첫 쓰기·verb 프로브) → PUT db/NODE → PUT db/ELEM.

라이브 쓰기 미검증: catalog 스키마 기반. 실제 MIDAS 쓰기 왕복은 QA 단계
또는 사용자가 빈 모델로 실행할 때 확인 필요. db/SWIND·portal PR #9 전례처럼
catalog ↔ 라이브 불일치 가능.
"""
from __future__ import annotations

import argparse
import os
import sys

import requests

from .geometry import GeometryError, build_model
from .template import TemplateError, read_template, write_template
from .writer import (DEFAULT_BASE_URL, LiveWriteUnsupported, MatlSectMissing,
                     ModelNotEmpty, WarehouseClient, WriteFailed,
                     check_matl_sect, empty_model_guard, id_overlap_warning,
                     put_unit, write_model)

EXIT_OK = 0
EXIT_ENV = 2
EXIT_WRITE = 3
EXIT_NOT_EMPTY = 4
EXIT_MATL_SECT = 5


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m tools.warehouse_frame_gen",
        description="창고 기본 프레임(그리드 + X방향 박공지붕) 생성기")
    p.add_argument("--template", help="입력 xlsx 폼 경로")
    p.add_argument("--make-template", metavar="PATH",
                   help="빈 입력 폼을 PATH 에 생성하고 종료")
    p.add_argument("--mapi-key", help="MAPI-Key (없으면 env MAPI_KEY)")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p.add_argument("--dry-run", action="store_true",
                   help="네트워크 호출 없이 생성 예정 카운트만 출력")
    p.add_argument("--force", action="store_true",
                   help="빈 모델이 아니어도 강제 진행(위험, id 겹침 경고)")
    return p


def _print_preview(model) -> None:
    c = model.counts
    m = model.meta
    print("── 생성 예정 (미리보기, 네트워크 호출 없음) ──")
    print(f"그리드 nx={m['nx']} ny={m['ny']} nz={m['nz']}  "
          f"matl={m['matl']} sect={m['sect']}  "
          f"node_start={m['node_start']} elem_start={m['elem_start']}")
    print(f"옵션: skip_bottom={m['skip_bottom_beam']} skip_top={m['skip_top_beam']} "
          f"use_ridge={m['use_ridge']} connect_rafters={m['connect_rafters']} "
          f"rafter_subdiv={m['rafter_subdiv']} num_purlins={m['num_purlins']} "
          f"rise={m['rise']}")
    print(f"절점 {c['nodes']}개")
    print(f"요소 {c['elements']}개  = X보 {c['x_beams']} / Y보 {c['y_beams']} / "
          f"기둥 {c['columns']} / 처마X보 {c['eave_x_beams']} / "
          f"용마루X보 {c['ridge_x_beams']} / 서까래 {c['rafters']} / "
          f"중도리보 {c['purlin_beams']}")


def _print_result(model, client, summary) -> None:
    c = model.counts
    m = model.meta
    print()
    print(f"[완료] 절점 {c['nodes']}개, 요소 {c['elements']}개  "
          f"(X보 {c['x_beams']} / Y보 {c['y_beams']} / 기둥 {c['columns']} / "
          f"처마X보 {c['eave_x_beams']} / 용마루X보 {c['ridge_x_beams']} / "
          f"서까래 {c['rafters']} / 중도리보 {c['purlin_beams']})")
    print(f"[배정] matl={m['matl']} sect={m['sect']}  "
          f"절점 id {m['node_start']}..{model.next_node_id - 1} / "
          f"요소 id {m['elem_start']}..{model.next_elem_id - 1}")
    print(f"[write] 요청 {len(client.request_log)}건, verb={client.verbs_used()}")
    print("[주의] 라이브 쓰기 미검증 — catalog 스키마 기반. 결과를 MIDAS 에서 확인 요망.")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.make_template:
        write_template(args.make_template)
        print(f"[완료] 빈 입력 폼 생성: {args.make_template}")
        return EXIT_OK

    if not args.template:
        print("Error: --template 필요 (또는 --make-template)", file=sys.stderr)
        return EXIT_ENV

    try:
        params = read_template(args.template)
    except (TemplateError, FileNotFoundError, OSError) as e:
        print(f"[템플릿 오류] {e}", file=sys.stderr)
        return EXIT_ENV

    try:
        model = build_model(params)
    except GeometryError as e:
        print(f"[입력 오류] {e}", file=sys.stderr)
        return EXIT_ENV
    for w in model.meta.get("warnings", []):
        print(f"[경고] {w}")

    if args.dry_run:
        _print_preview(model)
        return EXIT_OK

    key = args.mapi_key or os.environ.get("MAPI_KEY")
    if not key:
        print("Error: --mapi-key 또는 env MAPI_KEY 필요", file=sys.stderr)
        return EXIT_ENV
    client = WarehouseClient(key, base_url=args.base_url)

    try:
        empty_model_guard(client, force=args.force)
        check_matl_sect(client, params["matl"], params["sect"])
        if args.force:
            id_overlap_warning(client, model)
        put_unit(client)
        summary = write_model(client, model)
    except ModelNotEmpty as e:
        print(f"[중단] {e} (--force 로 우회 가능)", file=sys.stderr)
        return EXIT_NOT_EMPTY
    except MatlSectMissing as e:
        print(f"[중단] {e}", file=sys.stderr)
        return EXIT_MATL_SECT
    except LiveWriteUnsupported as e:
        print(f"[중단] {e}", file=sys.stderr)
        return EXIT_ENV
    except WriteFailed as e:
        print(f"[쓰기 실패] {e}", file=sys.stderr)
        return EXIT_WRITE
    except (requests.ConnectionError, requests.Timeout) as e:
        print(f"[중단] base_url 도달 불가 / 타임아웃: {e}", file=sys.stderr)
        return EXIT_ENV

    _print_result(model, client, summary)
    return EXIT_OK
