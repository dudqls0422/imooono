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


def build_all(out_dir: Path, preview: bool = True) -> list[Path]:
    """6개 DXF 를 out_dir 에 저장하고, preview 면 out_dir/preview 에 시트별 PNG 를 만든다."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fspec in FILES:
        doc = build_file(fspec)
        path = out_dir / fspec.filename
        doc.saveas(path)
        written.append(path)
        if preview:
            from .preview import render_previews
            written.extend(render_previews(doc, fspec, out_dir / "preview"))
    return written
