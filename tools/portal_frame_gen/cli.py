"""``python -m tools.portal_frame_gen`` 진입점.

흐름: 템플릿 읽기 → 형상 생성 → (dry-run 이면 출력 후 종료) →
PUT db/UNIT → 이름→id 해석 → 빈 모델 가드 → NODE/ELEM/CONS/GRUP PUT →
(선택) 읽기대조.

라이브 쓰기 미검증: catalog 스키마 기반 구현. 실제 MIDAS 쓰기 왕복은 QA
단계 또는 사용자가 빈 모델로 실행할 때 확인 필요. db/SWIND 전례처럼
catalog ↔ 라이브 불일치 가능.
"""
from __future__ import annotations

import argparse
import os
import sys

import requests

from .geometry import GeometryError, build_model
from .resolver import NamesNotFound, resolve_ids
from .template import TemplateError, read_template, write_template
from .verify import verify_model
from .writer import (DEFAULT_BASE_URL, LiveWriteUnsupported, ModelNotEmpty,
                     PortalFrameClient, WriteFailed, empty_model_guard, put_unit,
                     rollback, write_model)

EXIT_OK = 0
EXIT_ENV = 2
EXIT_WRITE = 3
EXIT_NOT_EMPTY = 4
EXIT_NAMES = 5


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m tools.portal_frame_gen",
        description="포탈(게이블) 프레임 모델 생성기 — MIDAS Gen NX 빈 모델에 PUT")
    p.add_argument("--template", help="입력 xlsx 템플릿 경로")
    p.add_argument("--mapi-key", help="MAPI-Key (없으면 env MAPI_KEY)")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p.add_argument("--dry-run", action="store_true",
                   help="네트워크 호출 없이 생성 예정 모델만 출력")
    p.add_argument("--force", action="store_true",
                   help="빈 모델이 아니어도 강제 진행(위험)")
    p.add_argument("--rollback", action="store_true",
                   help="쓰기 실패 시 역순 DELETE 시도(지원될 때만)")
    p.add_argument("--no-groups", action="store_true",
                   help="db/GRUP 생성 생략")
    p.add_argument("--make-template", metavar="PATH",
                   help="빈 템플릿(예시 1행)을 PATH 에 생성하고 종료")
    p.add_argument("--frame-mode", choices=["2D", "3D"],
                   help="템플릿의 frame_mode 를 오버라이드")
    p.add_argument("--verify", action="store_true",
                   help="생성 후 GET 으로 읽기대조")
    return p


def _print_preview(model) -> None:
    c = model.counts()
    print("── 생성 예정 모델 (미리보기, 네트워크 호출 없음) ──")
    m = model.meta
    print(f"span={m['span_m']} m, eave={m['eave_height_m']} m, "
          f"ridge={m['ridge_height_m']:.4f} m, 경사각={m['roof_angle_deg']:.2f}°, "
          f"mode={m['frame_mode']}, frames={m['n_frames']}, "
          f"bays={m['bay_count']}@{m['bay_spacing_m']} m")
    print(f"재료={m['material_name']}  기둥={m['column_section']}  "
          f"rafter={m['rafter_section']}  스트럿={m['eave_strut_section']}")
    print()
    print("[노드]  id  X        Y        Z")
    for n in model.nodes:
        print(f"       {n.id:>3}  {n.x:>7.3f}  {n.y:>7.3f}  {n.z:>7.3f}")
    print("[요소]  id  종류         n1   n2   단면")
    for e in model.elements:
        print(f"       {e.id:>3}  {e.kind:<11}  {e.n1:>3}  {e.n2:>3}  {e.section_name}")
    print("[지점]  node  구속(DX DY DZ RX RY RZ RW)")
    for s in model.supports:
        print(f"       {s.node_id:>4}  {s.constraint}")
    print("[그룹] " + ", ".join(f"{g.name}({len(g.elem_ids)})" for g in model.groups))
    print(f"── 합계: 노드 {c['nodes']} / 요소 {c['elements']} "
          f"(기둥 {c['columns']} / rafter {c['rafters']} / 스트럿 {c['eave_struts']}) "
          f"/ 지점 {c['supports']} / 그룹 {c['groups']}")


def _print_result(model, resolved, summary, client) -> None:
    c = model.counts()
    print()
    print(f"[완료] 노드 {c['nodes']} / 요소 {c['elements']} "
          f"(기둥 {c['columns']} / rafter {c['rafters']} / 스트럿 {c['eave_struts']}) "
          f"/ 지점 {c['supports']} / 그룹 {c['groups']}")
    print(f"[배정] 재료 id={resolved.material_id}  "
          + "  ".join(f"{name}→id {sid}"
                      for name, sid in resolved.section_ids.items()))
    print(f"[write] 요청 {len(client.request_log)}건, verb={client.verbs_used()}")
    print("[주의] 라이브 쓰기 미검증 — catalog 스키마 기반. 결과를 MIDAS 에서 확인 요망.")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.make_template:
        write_template(args.make_template)
        print(f"[완료] 빈 템플릿 생성: {args.make_template}")
        return EXIT_OK

    if not args.template:
        print("Error: --template 필요 (또는 --make-template)", file=sys.stderr)
        return EXIT_ENV

    try:
        params = read_template(args.template)
    except (TemplateError, FileNotFoundError, OSError) as e:
        print(f"[템플릿 오류] {e}", file=sys.stderr)
        return EXIT_ENV
    for w in params.warnings:
        print(f"[경고] {w}")
    if args.frame_mode:
        params.frame_mode = args.frame_mode
    try:
        model = build_model(params)
    except GeometryError as e:
        print(f"[형상 오류] {e}", file=sys.stderr)
        return EXIT_ENV

    if args.dry_run:
        _print_preview(model)
        return EXIT_OK

    key = args.mapi_key or os.environ.get("MAPI_KEY")
    if not key:
        print("Error: --mapi-key 또는 env MAPI_KEY 필요", file=sys.stderr)
        return EXIT_ENV
    client = PortalFrameClient(key, base_url=args.base_url)

    section_names = [params.column_section, params.rafter_section]
    if params.frame_mode == "3D":
        section_names.append(params.eave_strut_section)

    try:
        put_unit(client)
        resolved = resolve_ids(client, params.material_name, section_names)
        empty_model_guard(client, force=args.force)
        summary = write_model(client, model, resolved, no_groups=args.no_groups)
    except LiveWriteUnsupported as e:
        print(f"[중단] {e}", file=sys.stderr)
        return EXIT_ENV
    except NamesNotFound as e:
        print(f"[중단] {e}", file=sys.stderr)
        return EXIT_NAMES
    except ModelNotEmpty as e:
        print(f"[중단] {e} (--force 로 우회 가능)", file=sys.stderr)
        return EXIT_NOT_EMPTY
    except WriteFailed as e:
        print(f"[쓰기 실패] {e}", file=sys.stderr)
        if args.rollback:
            rollback(client, model)
        return EXIT_WRITE
    except (requests.ConnectionError, requests.Timeout) as e:
        print(f"[중단] base_url 도달 불가 / 타임아웃: {e}", file=sys.stderr)
        return EXIT_ENV

    if args.verify:
        problems = verify_model(client, model, resolved)
        if problems:
            print(f"[검증 실패] 읽기대조 불일치 {len(problems)}건", file=sys.stderr)
            return EXIT_WRITE

    _print_result(model, resolved, summary, client)
    return EXIT_OK
