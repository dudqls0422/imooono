"""M2 수정: 예제 10매(MOVE~ARRAY), 실습/정답 3매.

예제의 Before 는 수정 전 객체와 클릭 위치, After 는 수정 결과(원래 위치는 HIDDEN)를 보여준다.
실습은 왼쪽(또는 위)에 '시작 객체', 오른쪽(또는 아래)에 치수가 붙은 '완성 도형'을 둔다.
"""
from __future__ import annotations

import math

from ezdxf.enums import TextEntityAlignment

from ..common import Canvas
from ._layout import example, practice

MID = TextEntityAlignment.MIDDLE_CENTER


def _rotate(pt, base, deg):
    a = math.radians(deg)
    dx, dy = pt[0] - base[0], pt[1] - base[1]
    return (base[0] + dx * math.cos(a) - dy * math.sin(a),
            base[1] + dx * math.sin(a) + dy * math.cos(a))


def _corner_lines(f: Canvas, layer: str = "OUTLINE"):
    """모깎기·모따기 예제의 수정 전 두 선 (모서리에서 서로 튀어나옴)."""
    f.line((10, 20), (85, 20), layer)
    f.line((75, 10), (75, 90), layer)


# ── 예제 ──────────────────────────────────────────────────────────────

def e01_move(c: Canvas, spec):
    src = [(10, 10), (40, 10), (40, 30), (10, 30)]
    dst = [(x + 50, y + 30) for x, y in src]

    def before(f: Canvas):
        f.pline(src, closed=True)
        f.marker(1, src[0])
        f.marker(2, dst[0])
        f.text("@50,30", (dst[0][0] - 8, dst[0][1] + 8))

    def after(f: Canvas):
        f.pline(src, closed=True, layer="HIDDEN")
        f.pline(dst, closed=True)

    steps = ("명령: MOVE [Enter] (M)\\P"
             "객체 선택: 사각형 클릭 → [Enter]\\P"
             "기준점 지정 또는 [변위(D)] <변위>: ① 왼쪽 아래 끝점 (끝점 스냅)\\P"
             "두 번째 점 지정 또는 <첫 번째 점을 변위로 사용>: @50,30 [Enter] → ②\\P\\P"
             "[핵심 옵션] 변위(D)\\P"
             "D [Enter] → 50,30 [Enter] : 기준점 없이 이동량만 입력\\P\\P"
             "원래 위치(점선)에는 아무것도 남지 않는다.")
    example(c, spec, steps, before, after)


def e02_copy(c: Canvas, spec):
    centers = [(15, 40), (45, 40), (75, 40)]

    def before(f: Canvas):
        f.circle(centers[0], 8)
        for n, pt in enumerate(centers, 1):
            f.marker(n, pt)

    def after(f: Canvas):
        for pt in centers:
            f.circle(pt, 8)

    steps = ("명령: COPY [Enter] (CO)\\P"
             "객체 선택: 원 클릭 → [Enter]\\P"
             "기준점 지정 또는 [변위(D)/모드(O)] <변위>: ① 원의 중심 (중심 스냅)\\P"
             "두 번째 점 지정 또는 [배열(A)]: @30,0 [Enter] → ②\\P"
             "두 번째 점 지정 또는 [배열(A)/종료(E)/명령 취소(U)]: @60,0 [Enter] → ③\\P"
             "[Enter] 로 종료\\P\\P"
             "[핵심 옵션] 배열(A)\\P"
             "A [Enter] → 항목 수 3 → 두 번째 점 @30,0 : 같은 간격으로 한 번에 복사")
    example(c, spec, steps, before, after)


def e03_rotate(c: Canvas, spec):
    base = (20, 20)
    src = [(20, 20), (80, 20), (80, 40), (20, 40)]
    dst = [_rotate(p, base, 30) for p in src]

    def before(f: Canvas):
        f.pline(src, closed=True)
        f.marker(1, base)

    def after(f: Canvas):
        f.pline(src, closed=True, layer="HIDDEN")
        f.pline(dst, closed=True)
        f.text("30°", (70, 48))

    steps = ("명령: ROTATE [Enter] (RO)\\P"
             "현재 UCS 에서 양의 각도: 시계 반대 방향\\P"
             "객체 선택: 사각형 클릭 → [Enter]\\P"
             "기준점 지정: ① 왼쪽 아래 끝점\\P"
             "회전 각도 지정 또는 [복사(C)/참조(R)] <0>: 30 [Enter]\\P\\P"
             "[핵심 옵션] 복사(C)\\P"
             "C [Enter] → 30 [Enter] : 원본을 남기고 회전된 복사본 생성")
    example(c, spec, steps, before, after)


def e04_mirror(c: Canvas, spec):
    shape = [(10, 10), (40, 10), (40, 20), (20, 20), (20, 60), (10, 60)]
    mirrored = [(100 - x, y) for x, y in shape]

    def axis(f: Canvas):
        f.line((50, 0), (50, 70), layer="CENTER")

    def before(f: Canvas):
        axis(f)
        f.pline(shape, closed=True)
        f.marker(1, (50, 0))
        f.marker(2, (50, 70))

    def after(f: Canvas):
        axis(f)
        f.pline(shape, closed=True)
        f.pline(mirrored, closed=True)

    steps = ("명령: MIRROR [Enter] (MI)\\P"
             "객체 선택: L자 객체 클릭 → [Enter]\\P"
             "대칭선의 첫 번째 점 지정: ① 중심선 아래 끝점\\P"
             "대칭선의 두 번째 점 지정: ② 중심선 위 끝점 (F8 직교 켜면 편리)\\P"
             "원본 객체를 지우시겠습니까? [예(Y)/아니오(N)] <아니오>: [Enter]\\P\\P"
             "[핵심 옵션] 원본 지우기\\P"
             "N: 대칭 복사 (원본 유지)\\P"
             "Y: 뒤집기만 (원본 삭제)")
    example(c, spec, steps, before, after)


def e05_offset(c: Canvas, spec):
    def base(f: Canvas):
        f.rect(25, 25, 75, 65)
        f.line((10, 85), (90, 85))

    def before(f: Canvas):
        base(f)
        f.marker(1, (50, 25))
        f.marker(2, (50, 12))
        f.marker(3, (50, 85))
        f.marker(4, (50, 100))

    def after(f: Canvas):
        base(f)
        f.rect(15, 15, 85, 75)
        f.line((10, 95), (90, 95))

    steps = ("명령: OFFSET [Enter] (O)\\P"
             "간격띄우기 거리 지정 또는 [통과점(T)/지우기(E)/도면층(L)] <통과점>: 10 [Enter]\\P"
             "간격띄우기할 객체 선택: ① 사각형 클릭\\P"
             "간격띄우기할 면의 점 지정: ② 바깥쪽 클릭\\P"
             "간격띄우기할 객체 선택: ③ 선 클릭\\P"
             "간격띄우기할 면의 점 지정: ④ 위쪽 클릭\\P"
             "[Enter] 로 종료\\P\\P"
             "[핵심 옵션] 통과점(T)\\P"
             "거리 대신 지나갈 점을 클릭해 간격 지정\\P\\P"
             "폴리선은 전체가 한 번에 간격띄우기된다.")
    example(c, spec, steps, before, after)


def e06_trim(c: Canvas, spec):
    picks = [(10, 20), (90, 20), (10, 70), (90, 70), (20, 10), (80, 10), (20, 80), (80, 80)]

    def before(f: Canvas):
        f.line((0, 20), (100, 20))
        f.line((0, 70), (100, 70))
        f.line((20, 0), (20, 90))
        f.line((80, 0), (80, 90))
        for n, pt in enumerate(picks, 1):
            f.marker(n, pt)

    def after(f: Canvas):
        f.lines([(20, 20), (80, 20), (80, 70), (20, 70)], closed=True)

    steps = ("명령: TRIM [Enter] (TR)\\P"
             "현재 설정: 투영=UCS, 모서리=없음, 모드=빠른 작업\\P"
             "자를 객체 선택 또는 [절단 모서리(T)/걸치기(C)/모드(O)/프로젝트(P)/지우기(R)]:\\P"
             "  ① ~ ⑧ 튀어나온 부분을 하나씩 클릭\\P"
             "[Enter] 로 종료\\P\\P"
             "빠른 작업 모드: 경계를 따로 고르지 않아도 가장 가까운 교차점까지 잘린다.\\P\\P"
             "[핵심 옵션] 모드(O) → 표준(S)\\P"
             "절단 모서리를 먼저 선택하고 [Enter], 그다음 자를 부분 클릭 (이전 버전 방식)\\P\\P"
             "Tip: 걸치기(C)로 여러 부분을 한 번에 선택")
    example(c, spec, steps, before, after)


def e07_extend(c: Canvas, spec):
    rows = [(25, 40), (50, 55), (75, 30)]

    def boundary(f: Canvas):
        f.line((85, 10), (85, 90))

    def before(f: Canvas):
        boundary(f)
        for n, (y, x_end) in enumerate(rows, 1):
            f.line((10, y), (x_end, y))
            f.marker(n, (x_end - 5, y))

    def after(f: Canvas):
        boundary(f)
        for y, x_end in rows:
            f.line((10, y), (85, y))
            f.line((x_end, y - 3), (x_end, y + 3), layer="GUIDE")

    steps = ("명령: EXTEND [Enter] (EX)\\P"
             "현재 설정: 모드=빠른 작업\\P"
             "연장할 객체 선택 또는 [경계 모서리(B)/걸치기(C)/모드(O)/프로젝트(P)]:\\P"
             "  ① ② ③ 선의 오른쪽 끝 가까이 클릭\\P"
             "[Enter] 로 종료\\P\\P"
             "클릭한 쪽 끝이 가장 가까운 경계까지 늘어난다. (짧은 눈금: 원래 끝)\\P\\P"
             "[핵심 옵션] 경계 모서리(B)\\P"
             "경계선(오른쪽 세로선)을 먼저 지정해 그 선까지만 연장\\P\\P"
             "Tip: TRIM 중 Shift+클릭 → 연장 (EXTEND 중 Shift+클릭 → 자르기)")
    example(c, spec, steps, before, after)


def e08_fillet(c: Canvas, spec):
    r = 15.0

    def before(f: Canvas):
        _corner_lines(f)
        f.marker(1, (40, 20))
        f.marker(2, (75, 60))

    def after(f: Canvas):
        f.line((10, 20), (75 - r, 20))
        f.arc((75 - r, 20 + r), r, 270, 360)
        f.line((75, 20 + r), (75, 90))
        f.text("R15", (52, 40))

    steps = ("명령: FILLET [Enter] (F)\\P"
             "현재 설정: 모드 = 자르기, 반지름 = 0\\P"
             "첫 번째 객체 선택 또는 [명령 취소(U)/폴리선(P)/반지름(R)/자르기(T)/다중(M)]: R [Enter]\\P"
             "모깎기 반지름 지정 <0>: 15 [Enter]\\P"
             "첫 번째 객체 선택: ① 가로선\\P"
             "두 번째 객체 선택: ② 세로선\\P\\P"
             "클릭한 쪽이 남고 모서리가 호로 이어진다.\\P\\P"
             "[핵심 옵션]\\P"
             "반지름(R) 0: 두 선을 모서리로 정확히 맞춤\\P"
             "다중(M): 여러 모서리를 연속 처리")
    example(c, spec, steps, before, after)


def e09_chamfer(c: Canvas, spec):
    d = 10.0

    def before(f: Canvas):
        _corner_lines(f)
        f.marker(1, (40, 20))
        f.marker(2, (75, 60))

    def after(f: Canvas):
        f.line((10, 20), (75 - d, 20))
        f.line((75 - d, 20), (75, 20 + d))
        f.line((75, 20 + d), (75, 90))
        f.text("10 × 10", (48, 36))

    steps = ("명령: CHAMFER [Enter] (CHA)\\P"
             "(자르기 모드) 현재 모따기 거리1 = 0, 거리2 = 0\\P"
             "첫 번째 선 선택 또는 [… 거리(D) / 각도(A) … 다중(M)]: D [Enter]\\P"
             "첫 번째 모따기 거리 지정 <0>: 10 [Enter]\\P"
             "두 번째 모따기 거리 지정 <10>: [Enter]\\P"
             "첫 번째 선 선택: ①\\P"
             "두 번째 선 선택: ②\\P\\P"
             "[핵심 옵션]\\P"
             "거리(D): 두 선에서 잘라낼 길이\\P"
             "각도(A): 첫 번째 거리 + 각도로 지정")
    example(c, spec, steps, before, after)


def e10_array(c: Canvas, spec):
    cols, rows, dx, dy = 4, 3, 25.0, 25.0
    first = (15.0, 20.0)

    def before(f: Canvas):
        f.circle(first, 5)
        f.marker(1, (first[0] - 9, first[1] + 9))

    def after(f: Canvas):
        for j in range(rows):
            for i in range(cols):
                f.circle((first[0] + i * dx, first[1] + j * dy), 5)
        f.dim_linear(first, (first[0] + dx, first[1]), (27.5, 6))
        last_x = first[0] + (cols - 1) * dx
        f.dim_linear((last_x, first[1]), (last_x, first[1] + dy), (last_x + 12, 32.5), angle=90)

    steps = ("명령: ARRAYRECT [Enter] (AR → 직사각형(R))\\P"
             "객체 선택: ① 원 클릭 → [Enter]\\P"
             "유형 = 직사각형  연관 = 예\\P"
             "그립을 선택하여 배열 편집 또는 [… 개수(COU) / 간격두기(S) … 종료(X)]:\\P"
             "  COU [Enter] → 열 수 4 [Enter] → 행 수 3 [Enter]\\P"
             "  S [Enter] → 열 사이 거리 25 [Enter] → 행 사이 거리 25 [Enter]\\P"
             "  [Enter] 로 종료\\P\\P"
             "[핵심 옵션] 직사각형(R) / 원형(PO)\\P"
             "원형 배열은 중심점과 항목 수로 지정\\P\\P"
             "이 도면은 배열 결과를 개별 원으로 표시")
    example(c, spec, steps, before, after)


# ── 실습 / 정답 ───────────────────────────────────────────────────────

def _labels(f: Canvas, start_xy, done_xy):
    f.text("시작 객체 (여기서 작업)", start_xy, layer="GUIDE", align=MID)
    f.text("완성 도형", done_xy, layer="GUIDE", align=MID)


def p01_walls(c: Canvas, spec):
    w, h, t = 90.0, 50.0, 5.0

    def centerlines(f: Canvas):
        for y in (0, h):
            f.line((-10, y), (w + 10, y), layer="CENTER")
        for x in (0, w):
            f.line((x, -10), (x, h + 10), layer="CENTER")

    def figure(f0: Canvas, answer: bool):
        _labels(f0, (210, 205), (345, 205))
        centerlines(f0.at(165, 120))
        g = f0.at(300, 120)
        centerlines(g)
        g.lines([(-t, -t), (w + t, -t), (w + t, h + t), (-t, h + t)], closed=True)
        g.lines([(t, t), (w - t, t), (w - t, h - t), (t, h - t)], closed=True)
        g.dim_linear((0, h), (w, h), (w / 2, h + 18))
        g.dim_linear((0, 0), (0, h), (-20, h / 2), angle=90)
        g.dim_linear((w / 2, -t), (w / 2, t), (w / 2 + 6, 0), angle=90)
        if answer:
            g.marker(1, (30, -12))
            g.marker(2, (-14, -14))
            _trim_detail(f0.at(*TRIM_DETAIL_ORIGIN), t)

    steps = ("① OFFSET (O): 거리 5 → 중심선 4개를 각각 안·밖으로 간격띄우기 (8개 선)\\P"
             "    옵션 도면층(L) → 현재(C), 현재 도면층은 OUTLINE\\P"
             "② TRIM (TR) 빠른 작업 모드: 모서리 4곳 × 8번 = 32번 클릭\\P"
             "    중심선도 경계가 되므로 안쪽 선 끝은 세 조각으로 끊긴다.\\P"
             "    왼쪽 아래 모서리 (아래 확대도 1~8):\\P"
             "    1 바깥 가로선 끝   2 바깥 세로선 끝\\P"
             "    3·4·5 안쪽 가로선 세 조각 (바깥쪽부터)\\P"
             "    6·7·8 안쪽 세로선 세 조각 (바깥쪽부터)\\P"
             "    나머지 3 모서리도 같은 순서로 반복\\P"
             "    주의: 걸치기(C)·울타리(F)는 지나가는 선을 모두 자르므로 중심선·남길 선을 건너지 않게 한다\\P\\P"
             "벽 두께 10, 중심선은 CENTER 레이어로 유지")
    practice(c, spec, "왼쪽 시작 객체(벽 중심선)를 OFFSET 5 → TRIM 으로 정리", 10, steps, figure)


# 정답 확대도: 왼쪽 열 아래(안내문 영역 밖), 축척 ×4, 창 범위 -12~8 (도면 단위)
TRIM_DETAIL_ORIGIN = (68.0, 63.0)
TRIM_DETAIL_SCALE = 4.0


def _trim_detail(f: Canvas, t: float) -> None:
    """M2-A01 의 TRIM 전 왼쪽 아래 모서리 확대도 (GUIDE). 1~8 은 빠른 작업 모드 클릭 순서."""
    k = TRIM_DETAIL_SCALE
    lo, hi = -10.0, 8.0

    def seg(a, b, linetype=None):
        f.line((a[0] * k, a[1] * k), (b[0] * k, b[1] * k), layer="GUIDE", linetype=linetype)

    seg((lo, 0), (hi, 0), "CENTER")
    seg((0, lo), (0, hi), "CENTER")
    for d in (-t, t):
        seg((lo, d), (hi, d))
        seg((d, lo), (d, hi))
    picks = [(-7.5, -t), (-t, -7.5), (-7.5, t), (-2.5, t), (2.5, t), (t, -7.5), (t, -2.5), (t, 2.5)]
    for n, (x, y) in enumerate(picks, 1):
        f.marker(n, (x * k, y * k))
    f.text("TRIM 전 왼쪽 아래 모서리 확대 (×4)", (-48, 36), layer="GUIDE")


def p02_columns(c: Canvas, spec):
    xs_left, ys, axis_x = (0, 30, 60), (0, 40), 80.0
    xs_all = xs_left + tuple(2 * axis_x - x for x in reversed(xs_left))
    half = 6.0

    def grid(f: Canvas):
        for x in xs_all:
            f.line((x, -10), (x, 50), layer="CENTER")
        for y in ys:
            f.line((-10, y), (170, y), layer="CENTER")
        f.line((axis_x, -14), (axis_x, 54), layer="CENTER")
        f.text("대칭축", (axis_x, 59), align=MID)

    def column(f: Canvas, x, y):
        f.rect(x - half, y - half, x + half, y + half)

    def figure(f0: Canvas, answer: bool):
        f0.text("시작 객체 (여기서 작업)", (160, 228), layer="GUIDE")
        f0.text("완성 도형", (160, 140), layer="GUIDE")
        s = f0.at(200, 175)
        grid(s)
        column(s, 0, 0)
        g = f0.at(200, 80)
        grid(g)
        for x in xs_all:
            for y in ys:
                column(g, x, y)
        chain = list(xs_left) + [axis_x] + [2 * axis_x - x for x in reversed(xs_left)]
        for a, b in zip(chain, chain[1:]):
            g.dim_linear((a, -10), (b, -10), ((a + b) / 2, -16))
        g.dim_linear((-10, 0), (-10, 40), (-20, 20), angle=90)
        g.dim_linear((-half, 40 + half), (half, 40 + half), (0, 52))
        if answer:
            g.marker(1, (-14, 12))
            g.marker(2, (axis_x - 10, 52))
            g.marker(3, (axis_x, -25))

    steps = ("① ARRAY (AR) → 직사각형(R): 기둥 □12 선택 → 열 3, 행 2, 열 간격 30, 행 간격 40\\P"
             "② MIRROR (MI): 배열 선택 → 대칭축 위·아래 끝점 (②, ③) → 원본 지우기 N\\P\\P"
             "기둥은 그리드 교차점에 중심을 맞춤\\P"
             "치수는 참고용 표기(DIM 레이어)")
    practice(c, spec, "위쪽 시작 객체의 기둥 1개를 ARRAY 후 대칭축으로 MIRROR", 10, steps, figure)


def p03_beam(c: Canvas, spec):
    w, h, cover, ch, rf, rb = 60.0, 100.0, 8.0, 5.0, 7.0, 4.0
    fc = cover + rf
    bars = [(fc, fc), (w / 2, fc), (w - fc, fc), (fc, h - fc), (w - fc, h - fc)]

    def start(f: Canvas):
        f.lines([(0, 0), (w, 0), (w, h), (0, h)], closed=True)
        f.lines([(cover, cover), (w - cover, cover), (w - cover, h - cover), (cover, h - cover)],
                closed=True)
        f.circle((-22, 15), rb)

    def done(g: Canvas):
        # 바깥선: 네 모서리 모따기 5×5
        g.lines([(ch, 0), (w - ch, 0), (w, ch), (w, h - ch), (w - ch, h), (ch, h), (0, h - ch),
                 (0, ch)], closed=True)
        # 늑근: 네 모서리 모깎기 R7
        x0, y0, x1, y1 = cover, cover, w - cover, h - cover
        g.line((x0 + rf, y0), (x1 - rf, y0))
        g.line((x1, y0 + rf), (x1, y1 - rf))
        g.line((x1 - rf, y1), (x0 + rf, y1))
        g.line((x0, y1 - rf), (x0, y0 + rf))
        g.arc((x0 + rf, y0 + rf), rf, 180, 270)
        g.arc((x1 - rf, y0 + rf), rf, 270, 360)
        g.arc((x1 - rf, y1 - rf), rf, 0, 90)
        g.arc((x0 + rf, y1 - rf), rf, 90, 180)
        for b in bars:
            g.circle(b, rb)

    def figure(f0: Canvas, answer: bool):
        _labels(f0, (200, 225), (340, 225))
        start(f0.at(200, 105))
        g = f0.at(310, 105)
        done(g)
        g.dim_linear((0, h - ch), (w, h - ch), (w / 2, h + 10))
        g.dim_linear((w - ch, 0), (w - ch, h), (w + 14, h / 2), angle=90)
        g.dim_linear((0, h / 2), (cover, h / 2), (cover / 2, h / 2 + 8))
        g.dim_linear((w - ch, 0), (w, ch), (w - ch / 2, -8))
        # location 을 주면 치수점 방향이 중심→문자 위치로 정해지므로, 모깎기 호(0~90°) 쪽 바깥에 둔다
        g.dim_radius((w - fc, h - fc), rf, location=(w + 6, h + 4))
        g.dim_diameter(bars[1], rb, angle=60)
        if answer:
            g.marker(1, (-7, -7))
            g.marker(2, (w - cover - 2, h - cover - 22))
            g.marker(3, (fc, fc + 11))
            g.marker(4, (w / 2, fc + 10))

    steps = ("① CHAMFER (CHA): 거리 5, 5 → 바깥선 네 모서리 (다중(M) 옵션)\\P"
             "② FILLET (F): 반지름 7 → 늑근(안쪽선) 네 모서리\\P"
             "③ MOVE (M): 시작 철근 원 → 기준점 원의 중심 → 왼쪽 아래 모깎기 호의 중심 (중심 스냅)\\P"
             "④ COPY (CO): 기준점 철근 중심 → @15,0 · @30,0 (하단), @0,70 · @30,70 (상단)\\P\\P"
             "보 60×100, 피복 8, 철근 φ8\\P"
             "치수는 참고용 표기(DIM 레이어)")
    practice(c, spec, "모서리 정리(CHAMFER·FILLET) 후 철근을 MOVE 로 맞추고 COPY", 15, steps,
             figure)


BUILDERS = {
    "M2-E01": e01_move,
    "M2-E02": e02_copy,
    "M2-E03": e03_rotate,
    "M2-E04": e04_mirror,
    "M2-E05": e05_offset,
    "M2-E06": e06_trim,
    "M2-E07": e07_extend,
    "M2-E08": e08_fillet,
    "M2-E09": e09_chamfer,
    "M2-E10": e10_array,
    "M2-P01": p01_walls,
    "M2-P02": p02_columns,
    "M2-P03": p03_beam,
    "M2-A01": p01_walls,
    "M2-A02": p02_columns,
    "M2-A03": p03_beam,
}
