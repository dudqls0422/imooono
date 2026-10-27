"""예제·실습·정답 시트 양식 (도곽 왼쪽 아래 기준 로컬 좌표).

- 공통: 왼쪽 위 제목(높이 7), 왼쪽 열 안내문 MTEXT(x 20, 폭 118).
- 예제: 오른쪽에 Before(원점 160,100) → After(원점 295,100) 그림과 화살표.
- 실습/정답: 오른쪽 영역(x 150~405, y 60~255)에 시트별 그림. 정답은 같은 그림에 번호 원 추가.
"""
from __future__ import annotations

from typing import Callable

from ezdxf.enums import TextEntityAlignment

from ..common import TITLE_TEXT_H, Canvas
from ..manifest import ANSWER, EXAMPLE, SheetSpec

LEFT_X = 20.0
LEFT_TOP = 258.0
LEFT_W = 118.0
BEFORE_ORIGIN = (160.0, 100.0)
AFTER_ORIGIN = (295.0, 100.0)

Figure = Callable[[Canvas], None]


def _header(c: Canvas, spec: SheetSpec) -> None:
    """예제는 명령어가 주제라 제목 앞에 둔다. 실습/정답의 명령어는 표제란·힌트에 있다."""
    if spec.kind == EXAMPLE:
        s = f"{spec.sheet_id}  {spec.commands} — {spec.title} ({spec.kind})"
    else:
        s = f"{spec.sheet_id}  {spec.title} ({spec.kind})"
    c.text(s, (LEFT_X, 274.0), height=TITLE_TEXT_H)


def example(c: Canvas, spec: SheetSpec, steps: str, before: Figure, after: Figure,
            before_label: str = "Before", after_label: str = "After") -> None:
    _header(c, spec)
    c.mtext(steps, (LEFT_X, LEFT_TOP), LEFT_W)
    mid = TextEntityAlignment.MIDDLE_CENTER
    c.text(before_label, (BEFORE_ORIGIN[0] + 52, 232.0), layer="GUIDE", align=mid)
    c.text(after_label, (AFTER_ORIGIN[0] + 52, 232.0), layer="GUIDE", align=mid)
    before(c.at(*BEFORE_ORIGIN))
    after(c.at(*AFTER_ORIGIN))
    c.arrow((269.0, 150.0), (291.0, 150.0))


def practice(c: Canvas, spec: SheetSpec, hints: str, minutes: int, steps: str,
             figure: Callable[[Canvas, bool], None]) -> None:
    """실습/정답 공용. spec.kind 가 정답이면 작도 순서와 번호 원을 그린다."""
    _header(c, spec)
    answer = spec.kind == ANSWER
    if answer:
        body = "작도 순서 (그림의 번호 원과 대응)\\P\\P" + steps
    else:
        body = (f"이 도형을 그리시오.\\P\\P[사용 명령어]\\P{spec.commands}\\P\\P"
                f"[힌트]\\P{hints}\\P\\P[목표 시간] {minutes}분")
    c.mtext(body, (LEFT_X, LEFT_TOP), LEFT_W)
    figure(c, answer)
