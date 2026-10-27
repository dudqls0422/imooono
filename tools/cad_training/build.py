"""manifest 의 파일·시트 목록대로 DXF 문서를 만들고 저장한다."""
from __future__ import annotations

from pathlib import Path

from .common import SCALE_NOTE, Canvas, draw_frame, new_document, sheet_origin
from .manifest import FILES, FileSpec
from .sheets import BUILDERS


def build_file(fspec: FileSpec):
    """파일 하나의 시트들을 모델공간 X 방향으로 나열해 그린 문서를 돌려준다."""
    doc = new_document()
    msp = doc.modelspace()
    for i, spec in enumerate(fspec.sheets):
        c = Canvas(msp, *sheet_origin(i))
        draw_frame(c, [
            ("모듈", fspec.module),
            ("시트ID", spec.sheet_id),
            ("시트 종류", spec.kind),
            ("난이도", spec.level),
            ("명령어(단축키)", spec.title_commands or spec.commands),
            ("", SCALE_NOTE),
        ])
        BUILDERS[spec.sheet_id](c, spec)
    return doc


def freeze_class_order(doc) -> None:
    """CLASSES 섹션 순서를 이름순으로 고정한다.

    ezdxf 는 저장할 때 add_required_classes() 에서 사용 중인 엔티티 타입 set 을 순회하며
    클래스를 추가하므로, 문자열 hash 순서(PYTHONHASHSEED)에 따라 실행마다 순서가 바뀐다.
    저장 전에 같은 함수로 미리 등록하고 정렬해 두면, 저장 시점에는 새로 추가될 것이 없다.
    """
    doc.classes.add_required_classes(doc.dxfversion)
    ordered = sorted(doc.classes.classes.items())
    doc.classes.classes.clear()
    doc.classes.classes.update(ordered)


def build_all(out_dir: Path, preview: bool = True) -> list[Path]:
    """6개 DXF 를 out_dir 에 저장하고, preview 면 out_dir/preview 에 시트별 PNG 를 만든다."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fspec in FILES:
        doc = build_file(fspec)
        path = out_dir / fspec.filename
        freeze_class_order(doc)
        doc.saveas(path)
        written.append(path)
        if preview:
            from .preview import render_previews
            written.extend(render_previews(doc, fspec, out_dir / "preview"))
    return written
