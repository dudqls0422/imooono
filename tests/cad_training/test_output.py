"""생성된 DXF·PNG 검증 (Plan 스펙 T4 의 검사 1~9)."""
from __future__ import annotations

import ezdxf
import numpy as np
import pytest
from ezdxf import bbox
from PIL import Image

from tools.cad_training.common import FONT, LAYERS, SHEET_H, SHEET_W
from tools.cad_training.manifest import ANSWER, FILES, PRACTICE, all_sheets

FILE_IDS = [f.filename for f in FILES]
TOL = 1e-6


def _frames(doc):
    """FRAME 레이어의 닫힌 420×297 LWPOLYLINE 들의 (xmin, ymin, xmax, ymax), x 순 정렬."""
    out = []
    for e in doc.modelspace().query("LWPOLYLINE[layer=='FRAME']"):
        if not e.closed:
            continue
        ext = bbox.extents([e])
        if abs(ext.size.x - SHEET_W) < TOL and abs(ext.size.y - SHEET_H) < TOL:
            out.append((ext.extmin.x, ext.extmin.y, ext.extmax.x, ext.extmax.y))
    return sorted(out)


def _text_entities(doc):
    """모델공간과 모든 블록(치수 블록 포함)의 TEXT/MTEXT."""
    yield from doc.modelspace().query("TEXT MTEXT")
    for blk in doc.blocks:
        yield from blk.query("TEXT MTEXT")


@pytest.fixture(scope="module")
def docs(out):
    return {f.filename: ezdxf.readfile(out / f.filename) for f in FILES}


# 1. readfile + audit 오류 0
@pytest.mark.parametrize("name", FILE_IDS)
def test_audit_has_no_errors(out, name):
    doc = ezdxf.readfile(out / name)
    auditor = doc.audit()
    assert not auditor.has_errors, [str(e) for e in auditor.errors]
    assert doc.dxfversion == "AC1032"  # R2018
    assert doc.header["$INSUNITS"] == 4 and doc.header["$MEASUREMENT"] == 1


# 2. 도곽 수 = manifest 시트 수, 서로 겹치지 않음
@pytest.mark.parametrize("fspec", FILES, ids=FILE_IDS)
def test_frame_count_and_no_overlap(docs, fspec):
    frames = _frames(docs[fspec.filename])
    assert len(frames) == len(fspec.sheets)
    for a, b in zip(frames, frames[1:]):
        assert b[0] > a[2], f"도곽 겹침: {a} / {b}"


# 3. 각 도곽 안에 manifest 필수 엔티티 타입 존재 (도곽선·안내 표시 레이어 제외)
@pytest.mark.parametrize("fspec", FILES, ids=FILE_IDS)
def test_required_entities_inside_each_frame(docs, fspec):
    doc = docs[fspec.filename]
    frames = _frames(doc)
    found = [set() for _ in frames]
    cache = bbox.Cache()
    for e in doc.modelspace():
        if e.dxf.layer in ("FRAME", "GUIDE"):
            continue
        ext = bbox.extents([e], cache=cache)
        if not ext.has_data:
            continue
        for i, (x0, y0, x1, y1) in enumerate(frames):
            if (ext.extmin.x >= x0 - TOL and ext.extmax.x <= x1 + TOL
                    and ext.extmin.y >= y0 - TOL and ext.extmax.y <= y1 + TOL):
                found[i].add(e.dxftype())
                break
        else:
            pytest.fail(f"도곽 밖 엔티티: {e.dxftype()} {e.dxf.layer} {ext}")
    for spec, types in zip(fspec.sheets, found):
        missing = set(spec.required) - types
        assert not missing, f"{spec.sheet_id} 에 {missing} 없음 (있음: {sorted(types)})"


# 4. 필수 레이어 9개 (0 포함)
@pytest.mark.parametrize("name", FILE_IDS)
def test_required_layers(docs, name):
    names = {layer.dxf.name for layer in docs[name].layers}
    assert {"0", *LAYERS} <= names


# 5. 모든 TEXT/MTEXT 의 스타일 글꼴이 malgun.ttf
@pytest.mark.parametrize("name", FILE_IDS)
def test_all_text_uses_malgun(docs, name):
    doc = docs[name]
    texts = list(_text_entities(doc))
    assert texts
    bad = {(t.dxftype(), t.dxf.style) for t in texts
           if doc.styles.get(t.dxf.style).dxf.font.lower() != FONT}
    assert not bad


# 6. 모든 DIMENSION 에 geometry 블록이 있음 (render() 호출 확인)
@pytest.mark.parametrize("name", FILE_IDS)
def test_dimensions_are_rendered(docs, name):
    doc = docs[name]
    for d in doc.modelspace().query("DIMENSION"):
        block_name = d.dxf.get("geometry")
        assert block_name and block_name in doc.blocks, f"geometry 블록 없음: {d.dxf.handle}"
        assert len(doc.blocks.get(block_name)) > 0


# 7. PNG 가 시트 수만큼 있고 빈 이미지가 아님
def test_previews_exist_and_not_blank(out):
    sheets = all_sheets()
    pngs = sorted((out / "preview").glob("*.png"))
    assert sorted(p.stem for p in pngs) == sorted(s.sheet_id for s in sheets)
    for p in pngs:
        arr = np.asarray(Image.open(p).convert("L"), dtype=float)
        assert arr.var() > 50.0, f"빈 이미지로 보임: {p.name} (분산 {arr.var():.1f})"


# 8. 두 번 생성한 엔티티 덤프가 같음 (헤더 시각·GUID 는 엔티티가 아니므로 자연히 제외)
def _dump(doc):
    def norm(v):
        if hasattr(v, "x"):
            return tuple(round(c, 6) for c in v)
        if isinstance(v, float):
            return round(v, 6)
        return v

    rows = []
    layouts = [doc.modelspace(), *doc.blocks]
    for layout in layouts:
        for e in layout:
            attrs = e.dxfattribs(drop={"handle", "owner"})
            rows.append((e.dxftype(), sorted((k, norm(v)) for k, v in attrs.items()),
                         e.plain_text() if e.dxftype() == "MTEXT" else None,
                         list(e.get_points()) if e.dxftype() == "LWPOLYLINE" else None))
    return rows


@pytest.mark.parametrize("name", FILE_IDS)
def test_generation_is_deterministic(out, out2, name):
    assert _dump(ezdxf.readfile(out / name)) == _dump(ezdxf.readfile(out2 / name))


# 회귀: M1-A03 정답의 POLYGON 입력이 실습 도형과 같은 육각형을 만들어야 한다 (QA 반려 PR #14).
# AutoCAD POLYGON 외접(C)에 @R<θ 를 입력하면 변의 중점이 θ 에 오고 꼭짓점은 θ±30° 에 놓인다.
def _hexagon_vertex_angles(doc, frame_index):
    x0, y0, x1, y1 = _frames(doc)[frame_index]
    for e in doc.modelspace().query("LWPOLYLINE[layer=='OUTLINE']"):
        pts = [(p[0], p[1]) for p in e.get_points()]
        if len(pts) == 6 and all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in pts):
            cx = sum(x for x, _ in pts) / 6
            cy = sum(y for _, y in pts) / 6
            return sorted(round(np.degrees(np.arctan2(y - cy, x - cx)) % 360, 3) for x, y in pts)
    pytest.fail("육각형 LWPOLYLINE 없음")


def test_m1_a03_polygon_instruction_matches_figure(docs):
    import re

    files = {f.filename: f for f in FILES}
    p_idx = [s.sheet_id for s in files["M1_그리기.dxf"].sheets].index("M1-P03")
    a_idx = [s.sheet_id for s in files["M1_그리기_정답.dxf"].sheets].index("M1-A03")
    p_angles = _hexagon_vertex_angles(docs["M1_그리기.dxf"], p_idx)
    a_angles = _hexagon_vertex_angles(docs["M1_그리기_정답.dxf"], a_idx)
    assert p_angles == a_angles

    x0, y0, x1, y1 = _frames(docs["M1_그리기_정답.dxf"])[a_idx]
    steps = " ".join(m.plain_text() for m in docs["M1_그리기_정답.dxf"].modelspace().query("MTEXT")
                     if x0 <= m.dxf.insert.x <= x1)
    m = re.search(r"외접\(C\) → @(\d+)<(-?\d+)", steps)
    assert m, "정답의 POLYGON 단계에 @반지름<각도 입력이 없음"
    theta = float(m.group(2))
    expected = sorted(round((theta + 30 + 60 * k) % 360, 3) for k in range(6))
    assert a_angles == expected


# 9. 실습 Pxx 마다 정답 Axx 가 정확히 하나 (반대도 동일)
def test_practice_answer_pairs():
    sheets = all_sheets()
    practices = sorted(s.sheet_id for s in sheets if s.kind == PRACTICE)
    answers = sorted(s.sheet_id for s in sheets if s.kind == ANSWER)
    assert len(answers) == len(set(answers))
    assert [p.replace("-P", "-A") for p in practices] == answers
