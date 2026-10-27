"""C1 종합실습: 소규모 평면 일부 (실습/정답 각 1매).

그리드 3×2(간격 100), 기둥 □16 배열, 벽 두께 10(중심선 OFFSET 5 → TRIM),
문 2개(개구부 40, 문짝 LINE + 궤적 ARC, 두 번째 문은 X2 축 MIRROR). M1+M2 명령만 사용.
"""
from __future__ import annotations

from ezdxf.enums import TextEntityAlignment

from ..common import Canvas
from ._layout import practice

MID = TextEntityAlignment.MIDDLE_CENTER

XS = (0.0, 100.0, 200.0)
YS = (0.0, 100.0)
COL = 8.0
WALL = 5.0
DOOR = 40.0
# 아래 벽(Y1)의 문 개구부 (x 시작, x 끝, 경첩 x, 호 시작각, 호 끝각)
DOORS = ((30.0, 70.0, 30.0, 0.0, 90.0), (130.0, 170.0, 170.0, 90.0, 180.0))


def _wall_runs(a: float, b: float, gaps) -> list[tuple[float, float]]:
    """기둥 면 사이 벽 구간 [a+COL, b-COL] 에서 문 개구부를 뺀 구간들."""
    runs, cur = [], a + COL
    for g0, g1 in sorted(gaps):
        if a < g0 < b:
            runs.append((cur, g0))
            cur = g1
    runs.append((cur, b - COL))
    return runs


def _plan(f: Canvas) -> None:
    for i, x in enumerate(XS, 1):
        f.line((x, -15), (x, 118), layer="CENTER")
        f.circle((x, 124), 6)
        f.text(f"X{i}", (x, 124), align=MID)
    for i, y in enumerate(YS, 1):
        f.line((-15, y), (212, y), layer="CENTER")
        f.circle((-21, y), 6)
        f.text(f"Y{i}", (-21, y), align=MID)

    for x in XS:
        for y in YS:
            f.rect(x - COL, y - COL, x + COL, y + COL)

    door_gaps = [(d[0], d[1]) for d in DOORS]
    for y in YS:
        for xa, xb in zip(XS, XS[1:]):
            gaps = door_gaps if y == YS[0] else []
            for s in (-WALL, WALL):
                for r0, r1 in _wall_runs(xa, xb, gaps):
                    f.line((r0, y + s), (r1, y + s))
    for x in XS:
        for s in (-WALL, WALL):
            f.line((x + s, YS[0] + COL), (x + s, YS[1] - COL))

    for g0, g1, hinge, a0, a1 in DOORS:
        f.line((g0, -WALL), (g0, WALL))
        f.line((g1, -WALL), (g1, WALL))
        f.line((hinge, WALL), (hinge, WALL + DOOR))
        f.arc((hinge, WALL), DOOR, a0, a1)

    f.text("실 1", (50, 62), align=MID)
    f.text("실 2", (150, 62), align=MID)

    f.dim_linear((0, 0), (100, 0), (50, -28))
    f.dim_linear((100, 0), (200, 0), (150, -28))
    f.dim_linear((0, 0), (200, 0), (100, -40))
    f.dim_linear((-28, 0), (-28, 100), (-36, 50), angle=90)
    f.dim_linear((30, -WALL), (70, -WALL), (50, -16))
    f.dim_linear((192, -COL), (208, -COL), (200, -16), location=(215, -16))
    f.dim_linear((150, 100 - WALL), (150, 100 + WALL), (156, 100), angle=90)


def p01_plan(c: Canvas, spec):
    def figure(f0: Canvas, answer: bool):
        f = f0.at(190, 110)
        _plan(f)
        if answer:
            for n, pt in enumerate([(-12, 112), (14, 124), (-14, -13), (114, 86), (50, 112),
                                    (88, -13), (50, 14), (64, 38), (150, 30)], 1):
                f.marker(n, pt)

    hints = ("그리드 → 기둥 1개 → ARRAY → 벽 OFFSET·TRIM → 문 개구부 → 문짝·궤적 → MIRROR 순서 권장\\P"
             "그리드 간격 100, 기둥 □16, 벽 두께 10, 문 폭 40")
    steps = ("① LINE (L): 그리드 X1~X3, Y1~Y2 (간격 100, CENTER 레이어)\\P"
             "② CIRCLE (C): 그리드 버블 반지름 6\\P"
             "    버블 안 문자(X1… 등)는 참고 표기 — 문자 입력(TEXT)은 이 과정 범위 밖이므로 생략\\P"
             "③ RECTANG (REC): X1·Y1 기둥 □16 — 첫 구석점에서 FROM [Enter] → 기준점: X1·Y1 교차점 → "
             "간격띄우기: @-8,-8 → 다른 구석점 @16,16\\P"
             "④ ARRAY (AR): 직사각형 3열 × 2행, 간격 100 / 100\\P"
             "⑤ OFFSET (O): 그리드선을 양쪽 5 간격띄우기 (벽 두께 10)\\P"
             "⑥ TRIM (TR): 기둥 안쪽·벽 교차부 정리\\P"
             "⑦ LINE (L) + TRIM (TR): 문 개구부 40 — X1 에서 30·70 떨어진 곳에 문틀선 2개, 사이 벽선 자르기\\P"
             "⑧ LINE (L): 문짝 — 왼쪽 문틀선 위 끝점(경첩, 끝점 스냅) → @0,40 [Enter]\\P"
             "    ARC (A): C [Enter] → 중심: 경첩점 → 시작점: 오른쪽 문틀선 위 끝점 "
             "(끝점 스냅, = 경첩에서 @40,0) → 끝점: 문짝 위 끝점(끝점 스냅)\\P"
             "    호는 시작점에서 반시계 방향으로 90° 그려진다\\P"
             "⑨ MIRROR (MI): 실 1 의 문(개구부 포함)을 X2 축 기준 대칭 복사\\P\\P"
             "치수는 참고용 표기(DIM 레이어)")
    practice(c, spec, hints, 30, steps, figure)


BUILDERS = {
    "C1-P01": p01_plan,
    "C1-A01": p01_plan,
}
