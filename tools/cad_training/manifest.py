"""산출 DXF 파일별 시트 목록.

시트ID 규칙: <모듈>-E<nn>(예제) / -P<nn>(실습) / -A<nn>(정답, 같은 번호 실습과 1:1).
required 는 해당 도곽 안에 반드시 있어야 하는 엔티티 타입(테스트에서 검사).
시트는 목록 순서대로 모델공간 X 방향(피치 470)으로 놓인다.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

EXAMPLE = "예제"
PRACTICE = "실습"
ANSWER = "정답"


@dataclass(frozen=True)
class SheetSpec:
    sheet_id: str
    kind: str
    title: str
    commands: str
    level: str
    required: tuple[str, ...]
    # 표제란 명령어 칸에 넣을 짧은 표기 (commands 가 칸 폭을 넘을 때만 지정)
    title_commands: str = ""


@dataclass(frozen=True)
class FileSpec:
    filename: str
    module: str
    sheets: tuple[SheetSpec, ...]


def _ex(sid, title, commands, required, level="하"):
    return SheetSpec(sid, EXAMPLE, title, commands, level, ("MTEXT",) + required)


def _pr(sid, title, commands, required, level, title_commands=""):
    return SheetSpec(sid, PRACTICE, title, commands, level, ("MTEXT", "DIMENSION") + required,
                     title_commands)


def _answers(practices):
    return tuple(replace(p, sheet_id=p.sheet_id.replace("-P", "-A"), kind=ANSWER)
                 for p in practices)


M1_EXAMPLES = (
    _ex("M1-E01", "선 그리기", "LINE (L)", ("LINE",)),
    _ex("M1-E02", "원 그리기", "CIRCLE (C)", ("CIRCLE",)),
    _ex("M1-E03", "호 그리기", "ARC (A)", ("ARC",)),
    _ex("M1-E04", "직사각형 그리기", "RECTANG (REC)", ("LWPOLYLINE",)),
    _ex("M1-E05", "폴리선 그리기", "PLINE (PL)", ("LWPOLYLINE",)),
    _ex("M1-E06", "정다각형 그리기", "POLYGON (POL)", ("LWPOLYLINE", "CIRCLE")),
)
M1_PRACTICES = (
    _pr("M1-P01", "사각·원형 기둥 단면", "RECTANG (REC), CIRCLE (C), LINE (L)",
        ("LWPOLYLINE", "CIRCLE", "LINE"), "하"),
    _pr("M1-P02", "그리드 + 벽 외곽", "LINE (L), PLINE (PL), RECTANG (REC), CIRCLE (C)",
        ("LINE", "LWPOLYLINE", "CIRCLE"), "중"),
    _pr("M1-P03", "다각형 기초 평면 + 원형 개구부", "POLYGON (POL), CIRCLE (C), LINE (L)",
        ("LWPOLYLINE", "CIRCLE", "LINE"), "중"),
)

M2_EXAMPLES = (
    _ex("M2-E01", "객체 이동", "MOVE (M)", ("LWPOLYLINE",)),
    _ex("M2-E02", "객체 복사", "COPY (CO)", ("CIRCLE",)),
    _ex("M2-E03", "객체 회전", "ROTATE (RO)", ("LWPOLYLINE",)),
    _ex("M2-E04", "대칭 복사", "MIRROR (MI)", ("LWPOLYLINE", "LINE")),
    _ex("M2-E05", "간격띄우기", "OFFSET (O)", ("LWPOLYLINE", "LINE")),
    _ex("M2-E06", "자르기", "TRIM (TR)", ("LINE",)),
    _ex("M2-E07", "연장", "EXTEND (EX)", ("LINE",)),
    _ex("M2-E08", "모깎기", "FILLET (F)", ("LINE", "ARC")),
    _ex("M2-E09", "모따기", "CHAMFER (CHA)", ("LINE",)),
    _ex("M2-E10", "배열", "ARRAY (AR)", ("CIRCLE",)),
)
M2_PRACTICES = (
    _pr("M2-P01", "벽 중심선 OFFSET → TRIM 으로 벽체 만들기", "OFFSET (O), TRIM (TR)",
        ("LINE",), "중"),
    _pr("M2-P02", "기둥 ARRAY + MIRROR", "ARRAY (AR), MIRROR (MI)",
        ("LWPOLYLINE", "LINE"), "중"),
    _pr("M2-P03", "보 단면 FILLET/CHAMFER + 철근 COPY/MOVE",
        "FILLET (F), CHAMFER (CHA), COPY (CO), MOVE (M)", ("LINE", "ARC", "CIRCLE"), "상"),
)

C1_PRACTICES = (
    _pr("C1-P01", "소규모 평면 일부 종합",
        "LINE (L), RECTANG (REC), CIRCLE (C), ARC (A), OFFSET (O), TRIM (TR), ARRAY (AR), MIRROR (MI)",
        ("LINE", "LWPOLYLINE", "CIRCLE", "ARC"), "상",
        title_commands="L, REC, C, A, O, TR, AR, MI"),
)

FILES: tuple[FileSpec, ...] = (
    FileSpec("M1_그리기.dxf", "M1 그리기", M1_EXAMPLES + M1_PRACTICES),
    FileSpec("M1_그리기_정답.dxf", "M1 그리기", _answers(M1_PRACTICES)),
    FileSpec("M2_수정.dxf", "M2 수정", M2_EXAMPLES + M2_PRACTICES),
    FileSpec("M2_수정_정답.dxf", "M2 수정", _answers(M2_PRACTICES)),
    FileSpec("C1_종합실습.dxf", "C1 종합실습", C1_PRACTICES),
    FileSpec("C1_종합실습_정답.dxf", "C1 종합실습", _answers(C1_PRACTICES)),
)


# 실습 Pxx 와 정답 Axx 의 도형(GUIDE·TEXT·DIM·FRAME 레이어 제외)이 같지 않아도 되는 시트.
# 현재는 없다: 정답 시트는 실습과 같은 그림 함수로 시작 객체·완성 도형을 모두 그리고,
# 정답에만 추가되는 번호 원·확대도(M2-A01)는 GUIDE 레이어라 비교에서 빠진다.
ANSWER_FIGURE_EXCEPTIONS: frozenset[str] = frozenset()


def all_sheets() -> list[SheetSpec]:
    return [s for f in FILES for s in f.sheets]
