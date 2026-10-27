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


# 안내문 MTEXT 는 실제 렌더링 범위가 왼쪽 안내문 영역 안에 있고 다른 엔티티와 겹치지 않아야 한다.
# ezdxf.bbox 는 MTEXT 의 지정 폭만 쓰므로(긴 단어가 넘쳐도 모름) drawing 애드온으로 렌더링해 잰다.
TEXT_AREA = (15.0, 15.0, 145.0, 265.0)


def _rendered_extents(ctx, entity):
    from ezdxf.addons.drawing import Frontend
    from ezdxf.addons.drawing.recorder import Recorder

    rec = Recorder()
    Frontend(ctx, rec).draw_entities([entity])
    return rec.player().bbox()


@pytest.mark.parametrize("fspec", FILES, ids=FILE_IDS)
def test_guide_mtext_fits_text_area(docs, fspec):
    from ezdxf.addons.drawing import RenderContext

    doc = docs[fspec.filename]
    ctx = RenderContext(doc)
    msp = doc.modelspace()
    others = [(e, bbox.extents([e])) for e in msp if e.dxf.layer != "FRAME" and e.dxftype() != "MTEXT"]
    for i, (fx, fy, _, _) in enumerate(_frames(doc)):
        sid = fspec.sheets[i].sheet_id
        texts = [m for m in msp.query("MTEXT[layer=='TEXT']") if fx <= m.dxf.insert.x <= fx + SHEET_W]
        assert texts, f"{sid} 안내문 없음"
        for m in texts:
            b = _rendered_extents(ctx, m)
            x0, y0, x1, y1 = b.extmin.x - fx, b.extmin.y - fy, b.extmax.x - fx, b.extmax.y - fy
            assert (x0 >= TEXT_AREA[0] and y0 >= TEXT_AREA[1]
                    and x1 <= TEXT_AREA[2] and y1 <= TEXT_AREA[3]), \
                f"{sid} 안내문이 영역 밖: x {x0:.1f}~{x1:.1f}, y {y0:.1f}~{y1:.1f}"
            for e, eb in others:
                if not eb.has_data:
                    continue
                if (eb.extmin.x < b.extmax.x and eb.extmax.x > b.extmin.x
                        and eb.extmin.y < b.extmax.y and eb.extmax.y > b.extmin.y):
                    pytest.fail(f"{sid} 안내문이 {e.dxftype()}/{e.dxf.layer} 와 겹침")


# B7. 선종류 실효 길이 (A3 1:1 출력 기준 = 패턴 × $LTSCALE × 엔티티 ltscale)
LINETYPE_RULES = {"HIDDEN": (3.0, 1.5), "CENTER": (12.0, None)}  # (최소 대시, 최소 간격)


def _effective_linetype(doc, e):
    lt = e.dxf.get("linetype", "BYLAYER")
    if lt.upper() == "BYLAYER":
        lt = doc.layers.get(e.dxf.layer).dxf.linetype
    return lt.upper()


@pytest.mark.parametrize("name", FILE_IDS)
def test_linetype_effective_lengths(docs, name):
    doc = docs[name]
    ltscale = doc.header["$LTSCALE"]
    patterns = {}
    for lt_name in LINETYPE_RULES:
        tags = doc.linetypes.get(lt_name).pattern_tags.tags
        patterns[lt_name] = [t.value for t in tags if t.code == 49]
    used = set()
    for e in doc.modelspace():
        lt = _effective_linetype(doc, e)
        if lt not in LINETYPE_RULES:
            continue
        used.add(lt)
        k = ltscale * e.dxf.get("ltscale", 1.0)
        dashes = [v * k for v in patterns[lt] if v > 0]
        gaps = [-v * k for v in patterns[lt] if v < 0]
        min_dash, min_gap = LINETYPE_RULES[lt]
        if lt == "HIDDEN":
            assert min(dashes) >= min_dash and min(gaps) >= min_gap, (lt, dashes, gaps)
        else:
            assert max(dashes) >= min_dash, (lt, dashes)
    assert "CENTER" in used


# B8. 모든 문자 높이 ≥ 3.5 (TEXT, MTEXT, 치수 블록 문자), 표제란 문자는 칸 안에 들어감
MIN_TEXT_H = 3.5 - 1e-9


@pytest.mark.parametrize("name", FILE_IDS)
def test_text_height_lower_bound(docs, name):
    doc = docs[name]
    for t in _text_entities(doc):
        h = t.dxf.height if t.dxftype() == "TEXT" else t.dxf.char_height
        assert h >= MIN_TEXT_H, f"{t.dxftype()} 높이 {h}: {t.plain_text()[:30]}"
    # 치수 문자는 치수 블록의 MTEXT 로 위에서 함께 검사된다
    assert doc.dimstyles.get("EDU").dxf.dimtxt >= MIN_TEXT_H


@pytest.mark.parametrize("fspec", FILES, ids=FILE_IDS)
def test_title_block_text_fits_cells(docs, fspec):
    from tools.cad_training.common import BORDER, TITLE_W, text_width

    doc = docs[fspec.filename]
    for fx, fy, _, _ in _frames(doc):
        x1 = fx + SHEET_W - BORDER
        x0 = x1 - TITLE_W
        for t in doc.modelspace().query("TEXT[layer=='TEXT']"):
            ix, iy = t.dxf.align_point.x if t.dxf.halign else t.dxf.insert.x, t.dxf.insert.y
            if not (x0 <= ix <= x1 and fy + BORDER <= iy <= fy + BORDER + 40):
                continue
            right = ix + text_width(t.dxf.text, t.dxf.height)
            cell_right = x0 + TITLE_W / 2 if ix < x0 + TITLE_W / 2 and t.dxf.insert.y > fy + 30 else x1
            assert right <= cell_right - 2.5 + 1e-6, f"표제란 넘침: {t.dxf.text}"


# B9. 번호 원(GUIDE 원, bbox 정사각형)은 치수(선분·화살표·문자)나 다른 번호 원과 겹치지 않아야 한다
def _rect_overlap(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def _segment_hits_rect(p, q, r):
    """선분 pq 가 사각형 r(xmin, ymin, xmax, ymax)의 내부를 지나는지 (Liang–Barsky)."""
    t0, t1 = 0.0, 1.0
    dx, dy = q[0] - p[0], q[1] - p[1]
    for pk, qk in ((-dx, p[0] - r[0]), (dx, r[2] - p[0]), (-dy, p[1] - r[1]), (dy, r[3] - p[1])):
        if abs(pk) < 1e-12:
            if qk <= 0:
                return False
            continue
        t = qk / pk
        if pk < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 >= t1:
            return False
    return True


@pytest.mark.parametrize("fspec", FILES, ids=FILE_IDS)
def test_markers_do_not_overlap_dimensions_or_each_other(docs, fspec):
    from ezdxf.addons.drawing import RenderContext

    from tools.cad_training.common import MARKER_R

    doc = docs[fspec.filename]
    ctx = RenderContext(doc)
    msp = doc.modelspace()
    markers = []
    for c in msp.query("CIRCLE[layer=='GUIDE']"):
        if abs(c.dxf.radius - MARKER_R) < 1e-9:
            x, y = c.dxf.center.x, c.dxf.center.y
            markers.append((x - MARKER_R, y - MARKER_R, x + MARKER_R, y + MARKER_R))
    segments, rects = [], []
    for d in msp.query("DIMENSION"):
        for v in d.virtual_entities():
            if v.dxftype() == "LINE":
                segments.append(((v.dxf.start.x, v.dxf.start.y), (v.dxf.end.x, v.dxf.end.y)))
            else:
                b = _rendered_extents(ctx, v) if v.dxftype() == "MTEXT" else bbox.extents([v])
                if b.has_data:
                    rects.append((b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y))

    def where(m):
        i = int(m[0] // 470)
        return f"{fspec.sheets[i].sheet_id} ({m[0] - i * 470 + MARKER_R:.1f}, {m[1] + MARKER_R:.1f})"

    problems = []
    for i, m in enumerate(markers):
        if any(_segment_hits_rect(p, q, m) for p, q in segments):
            problems.append(f"{where(m)} 치수선과 겹침")
        if any(_rect_overlap(m, r) for r in rects):
            problems.append(f"{where(m)} 치수 문자·화살표와 겹침")
        if any(_rect_overlap(m, o) for o in markers[i + 1:]):
            problems.append(f"{where(m)} 다른 번호 원과 겹침")
    assert not problems, "\n".join(problems)


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
