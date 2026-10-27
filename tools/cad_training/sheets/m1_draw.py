"""M1 그리기: 예제 6매(LINE·CIRCLE·ARC·RECTANG·PLINE·POLYGON), 실습/정답 3매.

예제의 Before 는 클릭할 점(번호 원), After 는 명령 결과를 보여준다.
실습과 정답은 같은 그림 함수를 쓰고, 정답일 때만 작도 순서 번호 원을 더한다.
"""
from __future__ import annotations

import math

from ezdxf.enums import TextEntityAlignment

from ..common import Canvas
from ._layout import example, practice

MID = TextEntityAlignment.MIDDLE_CENTER
SMALL = 3.0


# ── 예제 ──────────────────────────────────────────────────────────────

def e01_line(c: Canvas, spec):
    a, b, p = (20, 20), (80, 20), (80, 70)
    labels = [(a, "20,20 (절대)", (-2, -8)), (b, "@60,0 (상대)", (-20, -8)),
              (p, "@50<90 (극좌표)", (-28, 8))]

    def before(f: Canvas):
        for n, (pt, s, off) in enumerate(labels, 1):
            f.marker(n, pt)
            f.text(s, (pt[0] + off[0], pt[1] + off[1]), height=SMALL)

    def after(f: Canvas):
        f.lines([a, b, p], closed=True)
        for pt, s, off in labels:
            f.text(s, (pt[0] + off[0], pt[1] + off[1]), height=SMALL)

    steps = ("명령: LINE [Enter] (L)\\P"
             "첫 번째 점 지정: 20,20 [Enter]\\P  → ① 절대좌표 (x,y)\\P"
             "다음 점 지정 또는 [명령 취소(U)]: @60,0 [Enter]\\P  → ② 상대좌표 (@x,y)\\P"
             "다음 점 지정 또는 [명령 취소(U)]: @50<90 [Enter]\\P  → ③ 극좌표 (@거리<각도)\\P"
             "다음 점 지정 또는 [닫기(C)/명령 취소(U)]: C [Enter]\\P\\P"
             "[좌표 입력 정리]\\P"
             "· 절대: 원점(0,0) 기준 x,y\\P"
             "· 상대: 직전 점 기준 @x,y\\P"
             "· 극좌표: 직전 점 기준 @거리<각도 (+X 축에서 반시계 방향 각도)\\P\\P"
             "[핵심 옵션]\\P닫기(C): 첫 점으로 닫고 종료\\P명령 취소(U): 직전 선분 취소")
    example(c, spec, steps, before, after, "Before: 클릭할 점", "After: 결과")


def e02_circle(c: Canvas, spec):
    o, big, small, r_t = (45, 60), 25.0, 12.0, 10.0
    tx = o[0] + math.sqrt((big + r_t) ** 2 - (o[1] - 20 - r_t) ** 2)
    t_center = (tx, 20 + r_t)
    k = big / (big + r_t)
    t_on_circle = (o[0] + (tx - o[0]) * k, o[1] + (t_center[1] - o[1]) * k)

    def base(f: Canvas):
        f.line((0, 20), (100, 20))

    def before(f: Canvas):
        base(f)
        f.marker(1, o)
        f.marker(2, (tx, 20))
        f.marker(3, t_on_circle)

    def after(f: Canvas):
        base(f)
        f.circle(o, big)
        f.circle(o, small)
        f.circle(t_center, r_t)

    steps = ("명령: CIRCLE [Enter] (C)\\P"
             "원에 대한 중심점 지정 또는 [3점(3P)/2점(2P)/Ttr(접선 접선 반지름)]: ①\\P"
             "원의 반지름 지정 또는 [지름(D)]: 25 [Enter]\\P\\P"
             "[OSNAP 중심] F3 으로 객체스냅 켜기\\P"
             "C [Enter] → 기존 원에 커서를 올려 중심 스냅 ① 클릭\\P"
             "반지름: 12 [Enter] (동심원)\\P\\P"
             "[OSNAP 접점 · Ttr 옵션]\\P"
             "C [Enter] → T [Enter]\\P"
             "첫 번째 접점: ② 선 위 클릭\\P"
             "두 번째 접점: ③ 큰 원 위 클릭\\P"
             "원의 반지름 지정: 10 [Enter]")
    example(c, spec, steps, before, after, "Before: 클릭할 점", "After: 결과")


def e03_arc(c: Canvas, spec):
    ctr, r = (50, 30), 40.0
    pts = [(10, 30), (50, 70), (90, 30)]

    def before(f: Canvas):
        for n, pt in enumerate(pts, 1):
            f.marker(n, pt)

    def after(f: Canvas):
        f.arc(ctr, r, 0, 180)
        f.line((ctr[0] - 5, ctr[1]), (ctr[0] + 5, ctr[1]), layer="CENTER")
        f.line((ctr[0], ctr[1] - 5), (ctr[0], ctr[1] + 5), layer="CENTER")

    steps = ("명령: ARC [Enter] (A)\\P"
             "호의 시작점 또는 [중심(C)] 지정: ①\\P"
             "호의 두 번째 점 또는 [중심(C)/끝(E)] 지정: ②\\P"
             "호의 끝점 지정: ③\\P\\P"
             "→ 세 점(3점)을 지나는 호가 그려진다.\\P\\P"
             "[핵심 옵션] 중심(C)\\P"
             "시작점 → C [Enter] → 중심점 → 끝점 순으로 지정\\P"
             "호는 시작점에서 반시계 방향으로 그려진다.")
    example(c, spec, steps, before, after, "Before: 클릭할 점", "After: 결과")


def e04_rectang(c: Canvas, spec):
    p1, p2 = (10, 20), (90, 70)

    def before(f: Canvas):
        f.marker(1, p1)
        f.marker(2, p2)
        f.text("@80,50", (p2[0] - 30, p2[1] + 8), height=SMALL)

    def after(f: Canvas):
        f.rect(*p1, *p2)
        f.text("80 × 50", ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2), height=SMALL, align=MID)

    steps = ("명령: RECTANG [Enter] (REC)\\P"
             "첫 번째 구석점 지정 또는 [모따기(C)/고도(E)/모깎기(F)/두께(T)/폭(W)]: ①\\P"
             "다른 구석점 지정 또는 [영역(A)/치수(D)/회전(R)]: @80,50 [Enter]\\P  → ②\\P\\P"
             "[핵심 옵션] 치수(D)\\P"
             "D [Enter] → 길이 80 [Enter] → 폭 50 [Enter] → 놓을 방향 클릭\\P\\P"
             "결과는 닫힌 폴리선 1개 (선 4개가 아님)")
    example(c, spec, steps, before, after, "Before: 클릭할 점", "After: 결과")


def e05_pline(c: Canvas, spec):
    pts = [(10, 20), (70, 20), (70, 60), (10, 60)]

    def before(f: Canvas):
        for n, pt in enumerate(pts, 1):
            f.marker(n, pt)

    def after(f: Canvas):
        f.pline([(10, 20), (70, 20, 1.0), (70, 60), (10, 60)], closed=True)

    steps = ("명령: PLINE [Enter] (PL)\\P"
             "시작점 지정: ①\\P"
             "다음 점 지정 또는 [호(A)/반폭(H)/길이(L)/명령 취소(U)/폭(W)]: @60,0 [Enter] → ②\\P"
             "다음 점: A [Enter] (호 모드)\\P"
             "호의 끝점 지정: @0,40 [Enter] → ③\\P"
             "호의 끝점: L [Enter] (선 모드로 복귀)\\P"
             "다음 점: @-60,0 [Enter] → ④\\P"
             "다음 점: C [Enter] (닫기)\\P\\P"
             "[핵심 옵션] 호(A) / 선(L) 전환\\P"
             "결과는 선과 호가 이어진 폴리선 1개")
    example(c, spec, steps, before, after, "Before: 클릭할 점", "After: 결과")


def e06_polygon(c: Canvas, spec):
    ctr, r = (50, 55), 35.0
    verts = [(ctr[0] + r * math.cos(math.radians(60 * i)),
              ctr[1] + r * math.sin(math.radians(60 * i))) for i in range(6)]

    def before(f: Canvas):
        f.marker(1, ctr)
        f.marker(2, verts[0])
        f.text("@35<0", (verts[0][0] - 12, verts[0][1] - 9), height=SMALL)

    def after(f: Canvas):
        f.circle(ctr, r, layer="HIDDEN")
        f.pline(verts, closed=True)
        f.text("가상 원 (내접)", (ctr[0], ctr[1] - r - 8), height=SMALL, align=MID)

    steps = ("명령: POLYGON [Enter] (POL)\\P"
             "면의 수 입력 <4>: 6 [Enter]\\P"
             "다각형의 중심 지정 또는 [모서리(E)]: ①\\P"
             "옵션 입력 [원에 내접(I)/원에 외접(C)] <I>: I [Enter]\\P"
             "원의 반지름 지정: @35<0 [Enter] → ②\\P\\P"
             "[핵심 옵션]\\P"
             "내접(I): 꼭짓점이 가상 원 위에 놓인다.\\P"
             "외접(C): 변의 중점이 가상 원 위에 놓인다.\\P"
             "  (기초 폭처럼 마주 보는 변 사이 거리가 정해질 때 사용)")
    example(c, spec, steps, before, after, "Before: 클릭할 점", "After: 결과")


# ── 실습 / 정답 ───────────────────────────────────────────────────────

def p01_columns(c: Canvas, spec):
    def figure(f: Canvas, answer: bool):
        # 사각 기둥 □100×100, 철근 φ8 (모서리에서 15 안쪽)
        f.line((165, 160), (285, 160), layer="CENTER")
        f.line((225, 100), (225, 220), layer="CENTER")
        f.rect(175, 110, 275, 210)
        bars = [(190, 125), (260, 125), (190, 195), (260, 195)]
        for b in bars:
            f.circle(b, 4)
        f.dim_linear((175, 210), (275, 210), (225, 225))
        f.dim_linear((175, 110), (175, 210), (160, 160), angle=90)
        f.dim_linear((175, 110), (190, 125), (182, 98))
        f.dim_diameter(bars[3], 4, angle=45)
        f.text("사각 기둥 □100×100 (철근 φ8)", (225, 80), align=MID)
        # 원형 기둥 φ100, 띠철근 φ80 (동심원)
        o = (345, 160)
        f.line((290, 160), (400, 160), layer="CENTER")
        f.line((345, 100), (345, 220), layer="CENTER")
        f.circle(o, 50)
        f.circle(o, 40)
        f.dim_diameter(o, 50, angle=45)
        f.dim_diameter(o, 40, angle=135)
        f.text("원형 기둥 φ100 (띠철근 φ80)", (345, 80), align=MID)
        if answer:
            f.marker(1, (232, 104))
            f.marker(2, (281, 104))
            f.marker(3, (202, 135))
            f.marker(4, (377, 113))
            f.marker(5, (318, 133))

    steps = ("① LINE (L): 중심선 2개씩 (CENTER 레이어)\\P"
             "② RECTANG (REC): 첫 점 클릭 → @100,100 [Enter]\\P"
             "③ CIRCLE (C): 철근 4개, 모서리에서 15 안쪽 점을 중심으로 반지름 4\\P"
             "④ CIRCLE (C): 원형 기둥, 중심선 교차점(교차점 스냅) → 반지름 50\\P"
             "⑤ CIRCLE (C): 띠철근, 중심 스냅 → 반지름 40 (동심원)\\P\\P"
             "치수는 참고용 표기(DIM 레이어)")
    practice(c, spec, "중심선을 먼저 그리고 교차점 스냅(F3)을 활용", 10, steps, figure)


def p02_grid_wall(c: Canvas, spec):
    xs, ys = (0, 100, 200), (0, 100)

    def figure(f0: Canvas, answer: bool):
        f = f0.at(185, 95)
        for i, x in enumerate(xs, 1):
            f.line((x, -15), (x, 120), layer="CENTER")
            f.circle((x, 126), 6)
            f.text(f"X{i}", (x, 126), align=MID)
        for i, y in enumerate(ys, 1):
            f.line((-15, y), (212, y), layer="CENTER")
            f.circle((-21, y), 6)
            f.text(f"Y{i}", (-21, y), align=MID)
        f.pline([(-10, -10), (210, -10), (210, 110), (-10, 110)], closed=True)
        f.rect(10, 10, 190, 90)
        f.dim_linear((0, -15), (100, -15), (50, -28))
        f.dim_linear((100, -15), (200, -15), (150, -28))
        f.dim_linear((-28, 0), (-28, 100), (-36, 50), angle=90)
        f.dim_linear((50, -10), (50, 10), (50, 0), angle=90)
        if answer:
            f.marker(1, (108, 60))
            f.marker(2, (100, 138))
            f.marker(3, (218, -18))
            f.marker(4, (180, 18))

    steps = ("① LINE (L): 그리드선 X1~X3 (간격 100), Y1~Y2 (간격 100) — CENTER 레이어\\P"
             "② CIRCLE (C): 그리드 버블 반지름 6 + 문자 X1~X3, Y1~Y2\\P"
             "③ PLINE (PL): 벽 바깥선 — 시작점에서 FROM [Enter] → 기준점: X1·Y1 교차점 → "
             "간격띄우기: @-10,-10 → @220,0 → @0,120 → @-220,0 → C\\P"
             "④ RECTANG (REC): 벽 안쪽선 — 첫 구석점에서 FROM [Enter] → 기준점: X1·Y1 교차점 → "
             "간격띄우기: @10,10 → 다른 구석점 @180,80\\P"
             "    (@ 는 마지막 점 기준이므로 교차점 기준 입력은 FROM 으로)\\P\\P"
             "벽 두께 20 (그리드 중심에서 양쪽 10)\\P"
             "치수는 참고용 표기(DIM 레이어)")
    practice(c, spec, "벽 두께 20 은 그리드선에서 양쪽 10 씩. 상대좌표(@)로 입력", 15, steps, figure)


def p03_footing(c: Canvas, spec):
    ap = 70.0
    rv = ap / math.cos(math.radians(30))
    verts = [(rv * math.cos(math.radians(30 + 60 * i)), rv * math.sin(math.radians(30 + 60 * i)))
             for i in range(6)]
    bolts = [(-40, -40), (40, -40), (40, 40), (-40, 40)]

    def figure(f0: Canvas, answer: bool):
        f = f0.at(275, 155)
        f.line((-90, 0), (90, 0), layer="CENTER")
        f.line((0, -90), (0, 90), layer="CENTER")
        f.pline(verts, closed=True)
        f.circle((0, 0), 20)
        for b in bolts:
            f.circle(b, 6)
        f.dim_linear(verts[3], verts[5], (0, -93))
        f.dim_linear((-40, 40), (40, 40), (0, 92))
        f.dim_diameter((0, 0), 20, angle=160)
        f.dim_diameter(bolts[1], 6, angle=-45)
        if answer:
            f.marker(1, (86, 8))
            f.marker(2, (-62, 62))
            f.marker(3, (14, 22))
            f.marker(4, (-52, -52))

    steps = ("① LINE (L): 중심선 (CENTER 레이어)\\P"
             "② POLYGON (POL): 6 [Enter] → 중심선 교차점 → 외접(C) → @70<0 [Enter]\\P"
             "    (변의 중점이 0° 방향 → 좌우 변이 수직, 마주 보는 변 사이 거리 140.\\P"
             "    반지름을 70 숫자로만 입력하면 아래 변이 수평으로 놓여 30° 돌아간 모양이 됨)\\P"
             "③ CIRCLE (C): 개구부 — 중심 스냅 → 반지름 20\\P"
             "④ CIRCLE (C): 앵커 구멍 4개 — 중심점 지정에서 FROM [Enter] → 기준점: 중심선 교차점 → "
             "간격띄우기: @40,40 (나머지 @-40,40 · @-40,-40 · @40,-40) → 반지름 6\\P\\P"
             "치수는 참고용 표기(DIM 레이어)")
    practice(c, spec, "대변 거리 140 이 주어졌으므로 POLYGON 외접(C) 옵션 사용", 12, steps, figure)


BUILDERS = {
    "M1-E01": e01_line,
    "M1-E02": e02_circle,
    "M1-E03": e03_arc,
    "M1-E04": e04_rectang,
    "M1-E05": e05_pline,
    "M1-E06": e06_polygon,
    "M1-P01": p01_columns,
    "M1-P02": p02_grid_wall,
    "M1-P03": p03_footing,
    "M1-A01": p01_columns,
    "M1-A02": p02_grid_wall,
    "M1-A03": p03_footing,
}
