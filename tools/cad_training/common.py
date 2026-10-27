"""CAD 교육자료 공통 기반.

문서 생성(R2018, mm 단위), 레이어·KOR 문자 스타일·EDU 치수 스타일,
A3 도곽·표제란, 모델공간 시트 배치 좌표, 시트 안 작도용 Canvas 를 제공한다.
모든 시트는 모델공간에 1:1 로 그리고, 시트 i 의 원점은 (i * 470, 0) 이다.
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

import ezdxf
from ezdxf.enums import MTextEntityAlignment, TextEntityAlignment

SHEET_W = 420.0
SHEET_H = 297.0
SHEET_GAP = 50.0
SHEET_PITCH = SHEET_W + SHEET_GAP
BORDER = 10.0
TITLE_W = 180.0
TITLE_H = 40.0

STYLE = "KOR"
FONT = "malgun.ttf"
DIMSTYLE = "EDU"
TEXT_H = 3.5
TITLE_TEXT_H = 7.0
SCALE_NOTE = "축척 1:1 (학습용 치수)"

# 레이어명: (색상 ACI, 선종류)
LAYERS = {
    "OUTLINE": (7, "Continuous"),
    "CENTER": (1, "CENTER"),
    "HIDDEN": (3, "HIDDEN"),
    "DIM": (2, "Continuous"),
    "TEXT": (4, "Continuous"),
    "HATCH": (8, "Continuous"),
    "FRAME": (5, "Continuous"),
    "GUIDE": (6, "Continuous"),
}

# ezdxf setup=True 는 HIDDEN 을 만들지 않으므로, 같은 스케일의 DASHED 패턴으로 직접 등록한다.
HIDDEN_PATTERN = [1.524, 1.27, -0.254]
LTSCALE = 2.0


def new_document() -> ezdxf.document.Drawing:
    """R2018 mm 문서를 만들고 레이어·문자·치수 스타일을 설정한다."""
    doc = ezdxf.new("R2018", setup=True, units=4)
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LTSCALE"] = LTSCALE
    if "HIDDEN" not in doc.linetypes:
        doc.linetypes.add("HIDDEN", HIDDEN_PATTERN, description="Hidden __ __ __ __")
    for name, (color, linetype) in LAYERS.items():
        doc.layers.add(name, color=color, linetype=linetype)
    doc.styles.add(STYLE, font=FONT)
    doc.dimstyles.new(DIMSTYLE, dxfattribs={
        "dimtxsty": STYLE,
        "dimtxt": TEXT_H,
        "dimasz": 2.5,
        "dimdec": 0,
        "dimexe": 1.5,
        "dimexo": 1.0,
        "dimgap": 1.0,
        "dimtad": 1,
        "dimtih": 0,
        "dimtoh": 0,
        "dimlunit": 2,
        "dimzin": 8,
    })
    return doc


def sheet_origin(index: int) -> tuple[float, float]:
    """시트 index(0부터) 의 도곽 왼쪽 아래 모델공간 좌표."""
    return (index * SHEET_PITCH, 0.0)


class Canvas:
    """원점을 옮긴 좌표계로 모델공간에 그리는 도우미. 좌표는 모두 mm."""

    def __init__(self, msp, ox: float = 0.0, oy: float = 0.0):
        self.msp = msp
        self.ox = ox
        self.oy = oy

    def at(self, dx: float, dy: float) -> "Canvas":
        return Canvas(self.msp, self.ox + dx, self.oy + dy)

    def p(self, x: float, y: float) -> tuple[float, float]:
        return (self.ox + x, self.oy + y)

    def line(self, a, b, layer: str = "OUTLINE"):
        return self.msp.add_line(self.p(*a), self.p(*b), dxfattribs={"layer": layer})

    def lines(self, pts: Sequence, layer: str = "OUTLINE", closed: bool = False):
        """점열을 개별 LINE 으로 잇는다 (LINE 명령 결과와 같은 형태)."""
        seq = list(pts) + ([pts[0]] if closed else [])
        return [self.line(a, b, layer) for a, b in zip(seq, seq[1:])]

    def circle(self, c, r: float, layer: str = "OUTLINE"):
        return self.msp.add_circle(self.p(*c), r, dxfattribs={"layer": layer})

    def arc(self, c, r: float, start: float, end: float, layer: str = "OUTLINE"):
        return self.msp.add_arc(self.p(*c), r, start, end, dxfattribs={"layer": layer})

    def pline(self, pts: Sequence, closed: bool = False, layer: str = "OUTLINE"):
        """pts 의 각 항목은 (x, y) 또는 (x, y, bulge)."""
        moved = [(self.ox + q[0], self.oy + q[1], 0, 0, q[2] if len(q) > 2 else 0)
                 for q in pts]
        return self.msp.add_lwpolyline(moved, format="xyseb", close=closed,
                                       dxfattribs={"layer": layer})

    def rect(self, x0, y0, x1, y1, layer: str = "OUTLINE"):
        return self.pline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True, layer=layer)

    def text(self, s: str, pos, height: float = TEXT_H, layer: str = "TEXT",
             align: TextEntityAlignment = TextEntityAlignment.MIDDLE_LEFT):
        t = self.msp.add_text(s, height=height, dxfattribs={"layer": layer, "style": STYLE})
        t.set_placement(self.p(*pos), align=align)
        return t

    def mtext(self, s: str, pos, width: float, height: float = TEXT_H, layer: str = "TEXT"):
        """pos 는 왼쪽 위 기준점. 줄바꿈은 \\P.

        자동 줄바꿈된 마지막 줄이 한 단어일 때 뒤따르는 \\P 가 ezdxf 렌더링에서 사라지므로
        \\P 앞에 공백을 넣는다 (AutoCAD 표시에는 영향 없음).
        """
        s = s.replace("\\P", " \\P")
        m = self.msp.add_mtext(s, dxfattribs={"layer": layer, "style": STYLE,
                                              "char_height": height, "width": width})
        m.set_location(self.p(*pos), attachment_point=MTextEntityAlignment.TOP_LEFT)
        return m

    def marker(self, n: int, pos, r: float = 3.5):
        """클릭 위치·작도 순서를 나타내는 번호 원 (GUIDE)."""
        self.circle(pos, r, layer="GUIDE")
        self.text(str(n), pos, height=TEXT_H * 0.8, layer="GUIDE",
                  align=TextEntityAlignment.MIDDLE_CENTER)

    def arrow(self, a, b, head: float = 5.0, width: float = 3.0):
        """a → b 화살표 (GUIDE). 머리는 폭이 줄어드는 폴리선 구간."""
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        hx, hy = b[0] - head * math.cos(ang), b[1] - head * math.sin(ang)
        self.line(a, (hx, hy), layer="GUIDE")
        return self.msp.add_lwpolyline(
            [(*self.p(hx, hy), width, 0, 0), (*self.p(*b), 0, 0, 0)],
            format="xyseb", dxfattribs={"layer": "GUIDE"})

    def dim_linear(self, p1, p2, base, angle: float = 0.0):
        d = self.msp.add_linear_dim(base=self.p(*base), p1=self.p(*p1), p2=self.p(*p2),
                                    angle=angle, dimstyle=DIMSTYLE,
                                    dxfattribs={"layer": "DIM"})
        d.render()
        return d

    def dim_diameter(self, c, r: float, angle: float = 45.0):
        d = self.msp.add_diameter_dim(center=self.p(*c), radius=r, angle=angle,
                                      dimstyle=DIMSTYLE, dxfattribs={"layer": "DIM"})
        d.render()
        return d

    def dim_radius(self, c, r: float, angle: float = 45.0):
        d = self.msp.add_radius_dim(center=self.p(*c), radius=r, angle=angle,
                                    dimstyle=DIMSTYLE, dxfattribs={"layer": "DIM"})
        d.render()
        return d


def draw_frame(c: Canvas, fields: Iterable[tuple[str, str]]) -> None:
    """A3 가로 도곽, 10mm 안쪽 테두리, 오른쪽 아래 180×40 표제란을 그린다.

    fields 는 (항목명, 값) 6개: 모듈, 시트ID, 시트 종류, 난이도, 명령어(단축키), 축척 순.
    항목명이 빈 문자열이면 값만 쓴다. 칸 폭을 넘는 문자열은 문자 높이를 줄인다.
    표제란은 4행 — 1·2행은 2칸씩, 3·4행은 전체 폭 1칸.
    """
    c.rect(0, 0, SHEET_W, SHEET_H, layer="FRAME")
    c.rect(BORDER, BORDER, SHEET_W - BORDER, SHEET_H - BORDER, layer="FRAME")
    x1, y0 = SHEET_W - BORDER, BORDER
    x0, y1 = x1 - TITLE_W, y0 + TITLE_H
    c.rect(x0, y0, x1, y1, layer="FRAME")
    row_h = TITLE_H / 4
    for i in range(1, 4):
        c.line((x0, y1 - i * row_h), (x1, y1 - i * row_h), layer="FRAME")
    xm = x0 + TITLE_W / 2
    c.line((xm, y1 - 2 * row_h), (xm, y1), layer="FRAME")

    cells = [(x0, 0, xm - x0), (xm, 0, x1 - xm), (x0, 1, xm - x0), (xm, 1, x1 - xm),
             (x0, 2, TITLE_W), (x0, 3, TITLE_W)]
    for (label, value), (cx, row, cell_w) in zip(fields, cells):
        s = f"{label}: {value}" if label else value
        h = min(TEXT_H * 0.85, (cell_w - 5) / _text_width_factor(s))
        c.text(s, (cx + 2.5, y1 - (row + 0.5) * row_h), height=h)


def _text_width_factor(s: str) -> float:
    """문자 높이 1 일 때의 대략적인 문자열 폭 (한글 1.0, 그 외 0.8 — 맑은고딕 대문자 기준 여유 포함)."""
    return sum(1.0 if ord(ch) > 0x2E80 else 0.8 for ch in s)
