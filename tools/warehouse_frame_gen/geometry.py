"""그리드 절점/요소 + X방향 용마루 지오메트리.

아래 5개 함수(``spans_to_coords`` / ``parse_span_expression`` /
``make_grid_nodes_indexed`` / ``make_grid_elements`` / ``add_ridge_roof``)는
원본 ``창고설계용 기본 프레임 생성.py`` 에서 **바이트 단위 그대로 이식**한
검증된 순수 함수다. 동작을 바꾸지 않는다. 원본에서 확인된 실제 동작은
``README.md`` 참조.

``build_model`` 은 원본 ``build_and_send`` 의 결합부에서 네트워크/GUI 를 뺀
지오메트리 조립만 담당한다(``--dry-run`` 이 이것만 씀).
"""
from __future__ import annotations

from .model import WarehouseModel


# =========================================================
# 원본 이식 — 아래 5개 함수는 한 글자도 바꾸지 않는다
# =========================================================
def spans_to_coords(spans, origin=0):
    """
    비등간격 스팬 리스트를 누적합하여 좌표 리스트로 변환
    spans  : [5, 3, 5, 3] 같은 간격 리스트 (기둥 사이 간격들)
    origin : 시작 좌표
    반환값 : 절점 개수 = len(spans)+1 인 좌표 리스트
    """
    coords = [origin]
    for s in spans:
        coords.append(coords[-1] + s)
    return coords


def parse_span_expression(text):
    """
    간격 리스트 문자열을 파싱하여 숫자 리스트로 변환.
    콤마(,)로 구분하며, 각 항목은 아래 두 형식을 지원한다.
      - "5"       : 간격 5 를 1회
      - "4@4"     : 간격(spacing) 4 를 4회 반복  ->  [4, 4, 4, 4]

    예) "2, 4@4, 2"  ->  [2, 4, 4, 4, 4, 2]
        (좌우 2m 간격 + 그 사이 4m 등간격 기둥 4개)
    """
    text = text.strip()
    if not text:
        raise ValueError("간격 리스트가 비어 있습니다. 예: 2, 4@4, 2")

    spans = []
    tokens = [t.strip() for t in text.split(",") if t.strip() != ""]
    if not tokens:
        raise ValueError("간격 리스트에 유효한 값이 없습니다.")

    for token in tokens:
        if "@" in token:
            parts = token.split("@")
            if len(parts) != 2:
                raise ValueError(f"형식 오류: '{token}' (예: 4@4 처럼 '간격@개수' 형태여야 합니다)")
            spacing_str, count_str = parts[0].strip(), parts[1].strip()
            try:
                spacing = float(spacing_str)
                count = int(count_str)
            except ValueError:
                raise ValueError(f"형식 오류: '{token}' (간격은 숫자, 개수는 정수여야 합니다)")
            if count <= 0:
                raise ValueError(f"형식 오류: '{token}' (반복 개수는 1 이상이어야 합니다)")
            spans.extend([spacing] * count)
        else:
            try:
                spans.append(float(token))
            except ValueError:
                raise ValueError(f"형식 오류: '{token}' (숫자 또는 '간격@개수' 형태로 입력하세요)")

    if any(s <= 0 for s in spans):
        raise ValueError("간격 값은 모두 0보다 커야 합니다.")

    return spans


def make_grid_nodes_indexed(x_vals, ny, dy, nz, dz, origin=(0, 0, 0), start_id=1):
    """
    X방향은 이미 계산된 좌표 리스트(x_vals, 등간격/비등간격 모두 지원)를 그대로 받고,
    Y/Z 방향은 기존처럼 등간격(개수+간격)으로 생성한다.
    """
    ox, oy, oz = origin
    y_vals = [oy + j * dy for j in range(ny)]
    z_vals = [oz + k * dz for k in range(nz)]

    node_assign = {}
    idx_to_id = {}
    node_id = start_id

    for k, z in enumerate(z_vals):
        for j, y in enumerate(y_vals):
            for i, x in enumerate(x_vals):
                node_assign[str(node_id)] = {"X": x, "Y": y, "Z": z}
                idx_to_id[(i, j, k)] = node_id
                node_id += 1

    return node_assign, idx_to_id, x_vals, y_vals, z_vals, node_id


def make_grid_elements(idx_to_id, nx, ny, nz, start_id=1, matl=1, sect=1,
                        skip_bottom_beam=False, skip_top_beam=False, skip_top_x_beam=False):
    """
    skip_bottom_beam : True이면 k=0 (최하부 층)에는 X/Y방향 보를 생성하지 않음
    skip_top_beam    : True이면 k=nz-1 (최상층/지붕층)에는 Y방향 보를 생성하지 않음
    skip_top_x_beam  : True이면 k=nz-1 (지붕층)의 X방향 보도 생성하지 않음
                        (용마루/서까래 세분화 기능이 지붕층 X방향 보를 직접 재구성하므로,
                         용마루 사용 시에는 여기서 중복 생성을 막기 위해 True로 설정)
    (기둥은 skip 옵션과 무관하게 항상 생성됨 - 기초/지붕 지지를 위해 필요)
    """
    elem_assign = {}
    elem_id = start_id
    top_k = nz - 1

    def is_skipped_x(k):
        if skip_bottom_beam and k == 0:
            return True
        if skip_top_x_beam and k == top_k:
            return True
        return False

    def is_skipped_y(k):
        if skip_bottom_beam and k == 0:
            return True
        if skip_top_beam and k == top_k:
            return True
        return False

    for k in range(nz):  # X방향 보
        if is_skipped_x(k):
            continue
        for j in range(ny):
            for i in range(nx - 1):
                elem_assign[str(elem_id)] = {
                    "TYPE": "BEAM", "MATL": matl, "SECT": sect,
                    "NODE": [idx_to_id[(i, j, k)], idx_to_id[(i + 1, j, k)]], "ANGLE": 0
                }
                elem_id += 1

    for k in range(nz):  # Y방향 보
        if is_skipped_y(k):
            continue
        for i in range(nx):
            for j in range(ny - 1):
                elem_assign[str(elem_id)] = {
                    "TYPE": "BEAM", "MATL": matl, "SECT": sect,
                    "NODE": [idx_to_id[(i, j, k)], idx_to_id[(i, j + 1, k)]], "ANGLE": 0
                }
                elem_id += 1

    for j in range(ny):  # Z방향 기둥 (항상 생성)
        for i in range(nx):
            for k in range(nz - 1):
                elem_assign[str(elem_id)] = {
                    "TYPE": "BEAM", "MATL": matl, "SECT": sect,
                    "NODE": [idx_to_id[(i, j, k)], idx_to_id[(i, j, k + 1)]], "ANGLE": 0
                }
                elem_id += 1

    return elem_assign, elem_id


def add_ridge_roof(node_assign, elem_assign, idx_to_id, x_vals, y_vals, z_vals,
                    rise, node_start_id, elem_start_id, matl=1, sect=1,
                    num_purlins=0, connect_rafters=True, rafter_subdiv=1):
    """
    X방향으로 지나가는 용마루(Ridge) + 처마 X방향 보 + 서까래(Rafter) + 중도리(Purlin) 생성
    기둥 사이 베이(bay)를 rafter_subdiv 만큼 등분하여, 기둥 위치뿐 아니라 그 사이 중간 위치에도
    평행한 서까래(및 처마보/용마루보 구간)를 추가로 생성한다.

    rafter_subdiv   : 기둥과 기둥 사이를 몇 등분할지 (1=추가 서까래 없음, 기존과 동일)
                       예) rafter_subdiv=2 이면 각 기둥 사이 중앙에 서까래가 1개씩 추가 생성됨
    num_purlins     : 처마-용마루 사이에 추가할 중도리 레벨 개수 (0이면 중도리 없음)
    connect_rafters : True이면 처마(지붕층 X방향 보) ↔ 용마루 연결부재(서까래)를 생성
                       False이면 용마루보(X방향)만 생성되고 서까래/중도리는 생성하지 않음
    """
    top_k = len(z_vals) - 1
    top_z = z_vals[top_k]
    y_mid = (y_vals[0] + y_vals[-1]) / 2
    nx = len(x_vals)
    ny = len(y_vals)

    node_id = node_start_id
    elem_id = elem_start_id

    # 0) 지붕 레벨 X위치 목록: 기둥 위치 + 베이별 중간 분할 위치
    roof_x = []
    for i in range(nx - 1):
        x0, x1 = x_vals[i], x_vals[i + 1]
        for s in range(rafter_subdiv):
            roof_x.append(x0 + (x1 - x0) * s / rafter_subdiv)
    roof_x.append(x_vals[-1])
    n_pos = len(roof_x)  # = (nx-1)*rafter_subdiv + 1

    def pos_is_column(pos_idx):
        return pos_idx % rafter_subdiv == 0

    def col_index(pos_idx):
        return pos_idx // rafter_subdiv

    # 1) 처마(지붕층) 절점 - 기둥 위치는 기존 절점 재사용, 중간 위치는 신규 생성
    eave_ids = {}  # (pos_idx, j) -> node_id
    for j in range(ny):
        for pos_idx in range(n_pos):
            if pos_is_column(pos_idx):
                eave_ids[(pos_idx, j)] = idx_to_id[(col_index(pos_idx), j, top_k)]
            else:
                node_assign[str(node_id)] = {"X": roof_x[pos_idx], "Y": y_vals[j], "Z": top_z}
                eave_ids[(pos_idx, j)] = node_id
                node_id += 1

    # 2) 용마루 절점 - 기둥 위치 + 중간 위치 모두 생성
    ridge_ids = {}  # pos_idx -> node_id
    for pos_idx in range(n_pos):
        node_assign[str(node_id)] = {"X": roof_x[pos_idx], "Y": y_mid, "Z": top_z + rise}
        ridge_ids[pos_idx] = node_id
        node_id += 1

    # 3) 처마 X방향 보 (지붕층 보) - 세분화된 위치들을 순차 연결
    for j in range(ny):
        for pos_idx in range(n_pos - 1):
            elem_assign[str(elem_id)] = {
                "TYPE": "BEAM", "MATL": matl, "SECT": sect,
                "NODE": [eave_ids[(pos_idx, j)], eave_ids[(pos_idx + 1, j)]], "ANGLE": 0
            }
            elem_id += 1

    # 4) 용마루보 (X방향) - 세분화된 위치들을 순차 연결
    for pos_idx in range(n_pos - 1):
        elem_assign[str(elem_id)] = {
            "TYPE": "BEAM", "MATL": matl, "SECT": sect,
            "NODE": [ridge_ids[pos_idx], ridge_ids[pos_idx + 1]], "ANGLE": 0
        }
        elem_id += 1

    if not connect_rafters:
        return node_id, elem_id

    # 5) 중도리(Purlin) 절점 - 처마와 용마루 사이를 (num_purlins+1) 등분
    n_div = num_purlins + 1
    purlin_ids = {}  # (j, d, pos_idx) -> node_id
    for j in range(ny):
        for d in range(1, num_purlins + 1):
            t = d / n_div
            for pos_idx in range(n_pos):
                ec = node_assign[str(eave_ids[(pos_idx, j)])]
                rc = node_assign[str(ridge_ids[pos_idx])]
                px = ec["X"] + (rc["X"] - ec["X"]) * t
                py = ec["Y"] + (rc["Y"] - ec["Y"]) * t
                pz = ec["Z"] + (rc["Z"] - ec["Z"]) * t
                node_assign[str(node_id)] = {"X": px, "Y": py, "Z": pz}
                purlin_ids[(j, d, pos_idx)] = node_id
                node_id += 1

    # 6) 서까래 - 처마(지붕층 X방향 보의 절점, 기둥위치+중간위치 전부) -> 중도리 -> 용마루
    for pos_idx in range(n_pos):
        for j in range(ny):
            chain = [eave_ids[(pos_idx, j)]]
            for d in range(1, num_purlins + 1):
                chain.append(purlin_ids[(j, d, pos_idx)])
            chain.append(ridge_ids[pos_idx])
            for a, b in zip(chain[:-1], chain[1:]):
                elem_assign[str(elem_id)] = {
                    "TYPE": "BEAM", "MATL": matl, "SECT": sect,
                    "NODE": [a, b], "ANGLE": 0
                }
                elem_id += 1

    # 7) 중도리보 (X방향) - 세분화된 위치들을 순차 연결
    for j in range(ny):
        for d in range(1, num_purlins + 1):
            for pos_idx in range(n_pos - 1):
                n1 = purlin_ids[(j, d, pos_idx)]
                n2 = purlin_ids[(j, d, pos_idx + 1)]
                elem_assign[str(elem_id)] = {
                    "TYPE": "BEAM", "MATL": matl, "SECT": sect,
                    "NODE": [n1, n2], "ANGLE": 0
                }
                elem_id += 1

    return node_id, elem_id


# =========================================================
# 이식 끝. 아래는 결합부(build_and_send) 재구성 + 입력 검증.
# =========================================================
class GeometryError(ValueError):
    """입력 파라미터가 형상적으로 성립하지 않음 (거부)."""


_REQUIRED_KEYS = (
    "x_spans", "ny", "dy", "nz", "dz", "ox", "oy", "oz",
    "matl", "sect", "node_start", "elem_start",
    "skip_bottom_beam", "skip_top_beam",
    "use_ridge", "rise", "connect_rafters", "rafter_subdiv", "num_purlins",
)


def validate_params(params: dict) -> list:
    """거부 규칙(GeometryError) 검사 + 경고 리스트 반환."""
    missing = [k for k in _REQUIRED_KEYS if k not in params]
    if missing:
        raise GeometryError(f"파라미터 누락: {', '.join(missing)}")

    spans = params["x_spans"]
    if not isinstance(spans, (list, tuple)) or len(spans) == 0:
        raise GeometryError("x_spans 가 비어 있음 (파싱된 간격 리스트 필요)")
    if any((not isinstance(s, (int, float))) or s <= 0 for s in spans):
        raise GeometryError(f"x_spans 간격은 모두 0 보다 커야 함: {spans}")

    if params["ny"] < 1:
        raise GeometryError(f"ny 는 1 이상: {params['ny']}")
    if params["nz"] < 1:
        raise GeometryError(f"nz 는 1 이상: {params['nz']}")
    if params["dy"] <= 0:
        raise GeometryError(f"dy 는 0 보다 커야 함: {params['dy']}")
    if params["dz"] <= 0:
        raise GeometryError(f"dz 는 0 보다 커야 함: {params['dz']}")
    if params["use_ridge"] and params["rise"] <= 0:
        raise GeometryError(f"use_ridge 인데 rise ≤ 0: {params['rise']}")
    if params["rafter_subdiv"] < 1:
        raise GeometryError(f"rafter_subdiv 는 1 이상: {params['rafter_subdiv']}")
    if params["num_purlins"] < 0:
        raise GeometryError(f"num_purlins 는 0 이상: {params['num_purlins']}")
    if params["node_start"] <= 0:
        raise GeometryError(f"node_start 는 1 이상: {params['node_start']}")
    if params["elem_start"] <= 0:
        raise GeometryError(f"elem_start 는 1 이상: {params['elem_start']}")
    if params["matl"] <= 0:
        raise GeometryError(f"matl 은 1 이상: {params['matl']}")
    if params["sect"] <= 0:
        raise GeometryError(f"sect 는 1 이상: {params['sect']}")

    warns = []
    nx = len(spans) + 1
    if params["nz"] == 1:
        warns.append("nz==1 — 기둥(Z방향 부재)이 생성되지 않음")
    if params["ny"] == 1:
        warns.append("ny==1 — Y방향 보가 없어 면외 방향 강성이 약함")
    if (params["skip_bottom_beam"] and params["skip_top_beam"]
            and params["nz"] <= 2):
        warns.append("skip_bottom+skip_top+nz≤2 — 횡방향이 준기구 상태일 수 있음")
    if params["use_ridge"]:
        roof_width = sum(spans)
        if params["rise"] > 0.5 * roof_width:
            warns.append(
                f"rise({params['rise']}) > 지붕폭({roof_width})의 0.5배 — 비현실적 물매")
    total_nodes_est = nx * params["ny"] * params["nz"]
    if total_nodes_est > 20000:
        warns.append(f"기본 그리드 절점 추정 {total_nodes_est}개 — 과다")
    return warns


def _derive_counts(params: dict, nx: int) -> dict:
    """표시용 카운트 분해 (원본 함수의 루프 구조에서 산술로 유도).

    build_model 이 반환하는 node_assign/elem_assign 길이가 authoritative 이며,
    이 분해의 합이 그와 일치하는지는 테스트가 검증한다.
    """
    ny, nz = params["ny"], params["nz"]
    sb, st, use_ridge = (params["skip_bottom_beam"], params["skip_top_beam"],
                         params["use_ridge"])
    top_k = nz - 1

    x_beams = sum((nx - 1) * ny for k in range(nz)
                  if not ((sb and k == 0) or (use_ridge and k == top_k)))
    y_beams = sum(nx * (ny - 1) for k in range(nz)
                  if not ((sb and k == 0) or (st and k == top_k)))
    columns = (nz - 1) * nx * ny
    base_nodes = nx * ny * nz

    eave_x = ridge_x = rafters = purlin_beams = 0
    eave_extra_nodes = ridge_nodes = purlin_nodes = 0
    if use_ridge:
        subdiv = params["rafter_subdiv"]
        n_pos = (nx - 1) * subdiv + 1
        eave_x = ny * (n_pos - 1)
        ridge_x = n_pos - 1
        eave_extra_nodes = ny * (n_pos - nx)
        ridge_nodes = n_pos
        if params["connect_rafters"]:
            npur = params["num_purlins"]
            rafters = n_pos * ny * (npur + 1)
            purlin_beams = ny * npur * (n_pos - 1)
            purlin_nodes = ny * npur * n_pos

    nodes = base_nodes + eave_extra_nodes + ridge_nodes + purlin_nodes
    elements = (x_beams + y_beams + columns + eave_x + ridge_x
                + rafters + purlin_beams)
    return {
        "nodes": nodes, "elements": elements,
        "x_beams": x_beams, "y_beams": y_beams, "columns": columns,
        "eave_x_beams": eave_x, "ridge_x_beams": ridge_x,
        "rafters": rafters, "purlin_beams": purlin_beams,
    }


def build_model(params: dict) -> WarehouseModel:
    """원본 build_and_send 의 지오메트리 조립부(네트워크/GUI 제외).

    파라미터 dict 키는 template.FIELDS 와 동일. x_spans 는 parse_span_expression
    결과(간격 리스트)여야 한다.
    """
    warns = validate_params(params)

    origin = (params["ox"], params["oy"], params["oz"])
    x_vals = spans_to_coords(params["x_spans"], origin=params["ox"])
    nx = len(x_vals)

    node_assign, idx_to_id, x_vals, y_vals, z_vals, next_node_id = \
        make_grid_nodes_indexed(
            x_vals=x_vals, ny=params["ny"], dy=params["dy"],
            nz=params["nz"], dz=params["dz"],
            origin=origin, start_id=params["node_start"])

    # 원본 결합: 용마루 사용 시 지붕층 X보는 add_ridge_roof 가 세분화해 재구성하므로
    # make_grid_elements 에서는 만들지 않는다(중복 방지). add_ridge_roof '전에' 적용.
    skip_top_x_beam = params["use_ridge"]
    elem_assign, next_elem_id = make_grid_elements(
        idx_to_id, nx=nx, ny=params["ny"], nz=params["nz"],
        start_id=params["elem_start"], matl=params["matl"], sect=params["sect"],
        skip_bottom_beam=params["skip_bottom_beam"],
        skip_top_beam=params["skip_top_beam"],
        skip_top_x_beam=skip_top_x_beam)

    if params["use_ridge"]:
        next_node_id, next_elem_id = add_ridge_roof(
            node_assign, elem_assign, idx_to_id, x_vals, y_vals, z_vals,
            rise=params["rise"],
            node_start_id=next_node_id, elem_start_id=next_elem_id,
            matl=params["matl"], sect=params["sect"],
            num_purlins=params["num_purlins"],
            connect_rafters=params["connect_rafters"],
            rafter_subdiv=params["rafter_subdiv"])

    counts = _derive_counts(params, nx)
    return WarehouseModel(
        node_assign=node_assign, elem_assign=elem_assign,
        next_node_id=next_node_id, next_elem_id=next_elem_id,
        counts=counts,
        meta={
            "x_vals": x_vals, "nx": nx, "ny": params["ny"], "nz": params["nz"],
            "matl": params["matl"], "sect": params["sect"],
            "node_start": params["node_start"], "elem_start": params["elem_start"],
            "skip_bottom_beam": params["skip_bottom_beam"],
            "skip_top_beam": params["skip_top_beam"],
            "use_ridge": params["use_ridge"],
            "connect_rafters": params["connect_rafters"],
            "rafter_subdiv": params["rafter_subdiv"],
            "num_purlins": params["num_purlins"],
            "rise": params["rise"],
            "warnings": warns,
        })
