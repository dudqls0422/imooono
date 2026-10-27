"""시트별 PNG 미리보기: 모델공간을 한 번 그린 뒤 도곽 bbox 로 잘라 저장한다."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from ezdxf.addons.drawing import Frontend, RenderContext  # noqa: E402
from ezdxf.addons.drawing.config import BackgroundPolicy, Configuration  # noqa: E402
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend  # noqa: E402

from .common import SHEET_H, SHEET_W, sheet_origin  # noqa: E402
from .manifest import FileSpec  # noqa: E402

DPI = 150


def render_previews(doc, fspec: FileSpec, out_dir: Path) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(SHEET_W / 25.4, SHEET_H / 25.4))
    ax = fig.add_axes((0, 0, 1, 1))
    config = Configuration(background_policy=BackgroundPolicy.WHITE)
    # adjust_figure=False: 그림 크기를 모델공간 전체(시트 나열) 비율로 바꾸지 않고 A3 비율 유지
    backend = MatplotlibBackend(ax, adjust_figure=False)
    Frontend(RenderContext(doc), backend, config=config).draw_layout(
        doc.modelspace(), finalize=True)
    # finalize 가 adjustable="datalim" 으로 두면 xlim 지정이 무시되므로 box 로 바꾼다.
    ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()
    written = []
    try:
        for i, spec in enumerate(fspec.sheets):
            x0, y0 = sheet_origin(i)
            ax.set_xlim(x0 - 2, x0 + SHEET_W + 2)
            ax.set_ylim(y0 - 2, y0 + SHEET_H + 2)
            path = out_dir / f"{spec.sheet_id}.png"
            fig.savefig(path, dpi=DPI, facecolor="white")
            written.append(path)
    finally:
        plt.close(fig)
    return written
