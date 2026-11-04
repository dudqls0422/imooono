"""구조계산서 양식(.xlsm) 검증 스크립트 — QA 완료 기준 1~5 / D8 을 PDF 실측으로 확인한다.

원본 .xlsm 은 건드리지 않고 출력 폴더에 사본을 만들어 그 사본으로만 시험한다.

    python -m tools.calc_sheet_template.verify_template --out-dir <폴더>

출력: fit.pdf / zoom100.pdf / multi.pdf / beforeprint.pdf / nodate.pdf, 각 페이지 PNG, report.json
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import pymupdf

from .build_template import (
    CALC_SHEET,
    DEFAULT_OUT,
    PAGE_MARGIN_TOP,
    SETTINGS_SHEET,
    ExcelSession,
    emit,
)

PT_PER_MM = 72 / 25.4
XL_NONE = -4142

PROJECT_AMP = "가나 & 다라 빌딩 신축공사"
PROJECT_SHORT = "테스트"
PROJECT_REFERENCE = "역삼동 641-8 근린생활시설 리모델링에 따른 구조안전진단"  # 참고본 실제 프로젝트명 (32자)
MIN_GAP_MM = 2.0  # 머리글 이미지 오른쪽 끝 ~ 프로젝트명 왼쪽 끝 최소 거리
PROJECT_BEFOREPRINT = "123동 & BeforePrint 확인"
DOC_DATE = "2026-11-04"


def mm(v: float) -> float:
    return round(v / PT_PER_MM, 2)


# ---------------------------------------------------------------- Excel 쪽 시나리오


def _fill_body(ws, rows: int) -> None:
    name = ws.Name
    ws.Range(f"A2:A{rows + 1}").Value = [[f"본문 {r}행 ({name})"] for r in range(2, rows + 2)]
    ws.Range(f"Z2:Z{rows + 1}").Value = [["Z"]] * rows


def _export_sheets(xl, wb, names: list[str], pdf: Path) -> None:
    wb.Activate()
    wb.Worksheets(names[0]).Activate()
    wb.Worksheets(names[0]).Select()
    for n in names[1:]:
        wb.Worksheets(n).Select(False)  # 추가 선택 (여러 시트를 한 번에 인쇄)
    xl.ActiveSheet.ExportAsFixedFormat(0, str(pdf))
    wb.Worksheets(names[0]).Select()


def run_excel(xl, work: Path, out: Path) -> dict:
    rec: dict = {}
    wb = xl.Workbooks.Open(str(work))
    try:
        settings = wb.Worksheets(SETTINGS_SHEET)
        calc = wb.Worksheets(CALC_SHEET)
        ps = calc.PageSetup
        rec["page_setup"] = {
            "zoom": ps.Zoom,
            "fit_wide": ps.FitToPagesWide,
            "fit_tall": ps.FitToPagesTall,
            "print_area": ps.PrintArea,
            "print_title_rows": ps.PrintTitleRows,
            "column_width": calc.Columns(1).ColumnWidth,
            "column_pt": calc.Columns(1).Width,
            "A_to_Z_pt": calc.Range("A1:Z1").Width,
            "left_margin_mm": mm(ps.LeftMargin),
            "right_margin_mm": mm(ps.RightMargin),
            "center_horizontally": ps.CenterHorizontally,
            "left_header": ps.LeftHeader,
            "left_footer": ps.LeftFooter,
        }
        val = settings.Range("C4").Validation
        rec["settings"] = {
            "print_area": settings.PageSetup.PrintArea,
            "project_validation": {"type": val.Type, "operator": val.Operator, "formula1": val.Formula1},
            "doc_date_format": settings.Range("C5").NumberFormat,
        }

        # 1) 배율: 맞춤(가로 1페이지) 출력과 100% 고정 출력을 비교. 열 경계는 임시 세로 테두리로 표시
        grid = calc.Range("A2:Z3")
        for edge in (7, 10, 11):  # 왼쪽, 오른쪽, 안쪽 세로
            grid.Borders(edge).LineStyle = 1
            grid.Borders(edge).Weight = 1  # xlHairline
        calc.Range("A2").Value = "A"
        calc.Range("Z2").Value = "Z"
        calc.ExportAsFixedFormat(0, str(out / "fit.pdf"))
        ps.Zoom = 100
        calc.ExportAsFixedFormat(0, str(out / "zoom100.pdf"))
        ps.Zoom = False
        ps.FitToPagesWide = 1
        ps.FitToPagesTall = False
        grid.Borders.LineStyle = XL_NONE
        calc.Range("A2:Z3").ClearContents()

        # 3) 설정 시트 입력 → Worksheet_Change 로 머리글 반영
        settings.Range("C4").Value = PROJECT_AMP
        settings.Range("C5").Value = DOC_DATE  # 사용자가 칸에 직접 친 것처럼 문자열로 넣는다 → Excel 이 날짜로 바꿈
        rec["doc_date_cell"] = {"value": str(settings.Range("C5").Value), "text": settings.Range("C5").Text}
        rec["right_header_after_change"] = calc.PageSetup.RightHeader

        # 2) 시트 복사 + 2페이지 이상 채우기 → 두 시트를 함께 출력
        before = {s.Name for s in wb.Worksheets}
        calc.Copy(None, calc)  # Before 생략, After = calc
        added = [s.Name for s in wb.Worksheets if s.Name not in before]
        if len(added) != 1:
            raise RuntimeError(f"시트 복사 결과를 찾지 못했습니다: {added}")
        copy = wb.Worksheets(added[0])
        rec["sheet_order"] = [s.Name for s in wb.Worksheets]
        rec["copied_sheet"] = copy.Name
        rec["right_header_copy"] = copy.PageSetup.RightHeader
        rec["left_header_copy"] = copy.PageSetup.LeftHeader
        rec["left_footer_copy"] = copy.PageSetup.LeftFooter
        rec["print_title_rows_copy"] = copy.PageSetup.PrintTitleRows
        _fill_body(calc, 130)
        _fill_body(copy, 70)
        _export_sheets(xl, wb, [calc.Name, copy.Name], out / "multi.pdf")

        # BeforePrint: 이벤트를 끈 채 값을 바꾼 뒤(머리글 미반영 상태) 다시 켜고 출력
        xl.EnableEvents = False
        settings.Range("C4").Value = PROJECT_BEFOREPRINT
        xl.EnableEvents = True
        rec["right_header_before_export"] = calc.PageSetup.RightHeader
        calc.ExportAsFixedFormat(0, str(out / "beforeprint.pdf"))
        rec["right_header_after_export"] = calc.PageSetup.RightHeader

        # 프로젝트명 길이별 (D4-2): 짧은 이름 / 참고본 이름(32자) / 입력 상한 글자 수 / 200자(유효성 검사 우회)
        max_chars = int(float(settings.Range("C4").Validation.Formula1))
        rec["project_max_chars"] = max_chars
        rec["project_cases"] = {}
        cases = {
            "short": PROJECT_SHORT,
            "reference": PROJECT_REFERENCE,
            "max": "가" * max_chars,
            "long200": ("가나다 & 라마바 " * 30)[:200],
        }
        for key, name in cases.items():
            # 이벤트에서 VBA 오류가 나면 대화상자가 떠 Excel 이 멈추므로, 이벤트를 끄고 Run 으로 직접 실행해 오류를 받는다
            xl.EnableEvents = False
            settings.Range("C4").Value = name
            xl.EnableEvents = True
            try:
                xl.Run(f"'{wb.Name}'!HeaderSync.UpdateHeaders")
                run_error = None
            except Exception as e:  # noqa: BLE001 - 결과 기록용
                run_error = repr(e)
            rh = calc.PageSetup.RightHeader
            line1 = rh.split("\n")[0]
            m = re.match(r"&(\d+)", line1)
            full = "&L" + calc.PageSetup.LeftHeader + "&C" + calc.PageSetup.CenterHeader + "&R" + rh
            rec["project_cases"][key] = {
                "input_len": len(name),
                "run_error": run_error,
                "left_header": calc.PageSetup.LeftHeader,
                "center_header": calc.PageSetup.CenterHeader,
                "right_header": rh,
                "font_pt": int(m.group(1)) if m else None,
                "ends_with_ellipsis": line1.endswith("…"),
                "total_len": len(full),
                "pdf": f"name_{key}.pdf",
            }
            calc.ExportAsFixedFormat(0, str(out / f"name_{key}.pdf"))
        settings.Range("C4").Value = PROJECT_BEFOREPRINT

        # 작성일 비움 → 변경 이벤트로 반영, 복사본에도 반영됐는지 함께 기록
        settings.Range("C5").ClearContents()
        rec["right_header_nodate"] = calc.PageSetup.RightHeader
        rec["right_header_nodate_copy"] = copy.PageSetup.RightHeader
        calc.ExportAsFixedFormat(0, str(out / "nodate.pdf"))
    finally:
        wb.Close(False)
    return rec


# ---------------------------------------------------------------- PDF 분석


def _spans(page):
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            for s in line["spans"]:
                if s["text"].strip():
                    yield s


def _img(i) -> dict:
    x0, y0, x1, y1 = i["bbox"]
    w_in, h_in = (x1 - x0) / 72, (y1 - y0) / 72
    return {
        "bbox_mm": [mm(x0), mm(y0), mm(x1), mm(y1)],
        "size_mm": [mm(x1 - x0), mm(y1 - y0)],
        "aspect_w_over_h": round((x1 - x0) / (y1 - y0), 3),
        "pixels": [i["width"], i["height"]],
        "dpi": [round(i["width"] / w_in), round(i["height"] / h_in)],
    }


def analyze_page(page) -> dict:
    h = page.rect.height
    top_zone = PAGE_MARGIN_TOP * PT_PER_MM
    footer_zone = h - 30 * PT_PER_MM
    spans = list(_spans(page))
    header = [s for s in spans if s["bbox"][3] <= top_zone]
    body = [s for s in spans if s["bbox"][1] > top_zone and s["bbox"][3] < footer_zone]
    images = page.get_image_info()
    head_imgs = [i for i in images if i["bbox"][3] <= top_zone]
    foot_imgs = [i for i in images if i["bbox"][1] >= footer_zone]
    rules = [
        d["rect"]
        for d in page.get_drawings()
        if d["rect"].width > 400 and d["rect"].height < 4 and d["rect"].y0 < 40 * PT_PER_MM
    ]
    header_bottom = max([s["bbox"][3] for s in header] + [i["bbox"][3] for i in head_imgs] + [0])
    rule_top = min((r.y0 for r in rules), default=None)
    rule_x = [mm(min(r.x0 for r in rules)), mm(max(r.x1 for r in rules))] if rules else None
    body_top = min((s["bbox"][1] for s in body), default=None)
    body_bottom = max((s["bbox"][3] for s in body), default=None)
    footer_top = min((i["bbox"][1] for i in foot_imgs), default=None)
    return {
        "header_text": [(s["text"], round(s["size"], 1), s["font"]) for s in header],
        "header_logo": [_img(i) for i in head_imgs],
        "footer_image": [_img(i) for i in foot_imgs],
        "rule_y_mm": mm(rule_top) if rule_top is not None else None,
        "rule_x_mm": rule_x,
        "header_bottom_mm": mm(header_bottom),
        "body_top_mm": mm(body_top) if body_top is not None else None,
        "body_bottom_mm": mm(body_bottom) if body_bottom is not None else None,
        "footer_top_mm": mm(footer_top) if footer_top is not None else None,
        "gap_header_to_rule_mm": mm(rule_top - header_bottom) if rule_top is not None else None,
        "gap_body_to_footer_mm": (
            mm(footer_top - body_bottom) if footer_top is not None and body_bottom is not None else None
        ),
    }


def _header_lines(page) -> list[tuple[str, list[float]]]:
    """머리글 영역(위 여백 안)의 글줄 (글자, bbox mm)."""
    top_zone = PAGE_MARGIN_TOP * PT_PER_MM
    out = []
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            text = "".join(s["text"] for s in line["spans"]).strip()
            if text and line["bbox"][3] <= top_zone:
                out.append((text, [mm(v) for v in line["bbox"]]))
    return out


def column_lines(page) -> list[float]:
    xs = set()
    for d in page.get_drawings():
        r = d["rect"]
        if r.width < 2 and r.height > 5 and r.y0 < 60 * PT_PER_MM:
            xs.add(round((r.x0 + r.x1) / 2, 2))
    return sorted(xs)


def render(pdf: Path, out: Path, dpi: int = 110) -> list[str]:
    names = []
    with pymupdf.open(pdf) as doc:
        for i, page in enumerate(doc, 1):
            p = out / f"{pdf.stem}_p{i}.png"
            page.get_pixmap(dpi=dpi).save(p)
            names.append(p.name)
    return names


def analyze(out: Path, rec: dict) -> dict:
    report: dict = {"excel": rec}
    with pymupdf.open(out / "fit.pdf") as fit, pymupdf.open(out / "zoom100.pdf") as z100:
        xf, xz = column_lines(fit[0]), column_lines(z100[0])
        widths = [round(b - a, 3) for a, b in zip(xf, xf[1:])]
        report["fit"] = {
            "pages": fit.page_count,
            "column_lines_fit_pt": xf,
            "column_lines_zoom100_pt": xz,
            "identical_to_zoom100": xf == xz,
            "n_columns_measured": len(widths),
            "column_width_pt": sorted(set(widths)),
            "column_width_mm": sorted({mm(w) for w in widths}),
            "A_to_Z_mm": mm(xf[-1] - xf[0]) if xf else None,
            "left_mm": mm(xf[0]) if xf else None,
            "right_mm": mm(xf[-1]) if xf else None,
            "effective_scale": (
                round((xf[-1] - xf[0]) / float(rec["page_setup"]["A_to_Z_pt"]), 4) if xf else None
            ),
            "page_1": analyze_page(fit[0]),
        }
        # 머리글 선(1행 테두리) / 본문 A~Z(열 경계) / 바닥글 이미지(선)의 왼쪽·오른쪽 끝 비교 (기준 0.5mm)
        p1 = report["fit"]["page_1"]
        ends = {"header_rule": p1["rule_x_mm"], "body_A_to_Z": [mm(xf[0]), mm(xf[-1])] if xf else None}
        if p1["footer_image"]:
            fb = p1["footer_image"][0]["bbox_mm"]
            ends["footer_rule"] = [fb[0], fb[2]]
        lefts = [v[0] for v in ends.values() if v]
        rights = [v[1] for v in ends.values() if v]
        header_left = p1["header_logo"][0]["bbox_mm"][0] if p1["header_logo"] else None
        report["alignment"] = {
            "ends_mm": ends,
            "header_image_left_mm": header_left,
            "header_image_left_diff_mm": round(header_left - ends["body_A_to_Z"][0], 2) if header_left else None,
            "left_spread_mm": round(max(lefts) - min(lefts), 2),
            "right_spread_mm": round(max(rights) - min(rights), 2),
            "within_0_5mm": len(lefts) == 3
            and max(lefts) - min(lefts) <= 0.5
            and max(rights) - min(rights) <= 0.5
            and header_left is not None
            and abs(header_left - ends["body_A_to_Z"][0]) <= 0.5,
        }
    for name in ("multi", "beforeprint", "nodate"):
        with pymupdf.open(out / f"{name}.pdf") as doc:
            report[name] = {"pages": doc.page_count, "page_detail": [analyze_page(p) for p in doc]}

    # 프로젝트명 길이별: 머리글 이미지 오른쪽 끝 ~ 프로젝트명 왼쪽 끝 거리 (≥ 2mm 이면 겹치지 않음)
    report["project_cases"] = {}
    for key, case in rec.get("project_cases", {}).items():
        with pymupdf.open(out / case["pdf"]) as doc:
            page = doc[0]
            detail = analyze_page(page)
            img = detail["header_logo"][0]["bbox_mm"] if detail["header_logo"] else None
            lines = [
                (t, bb)
                for t, bb in _header_lines(page)
                if " / " not in t and not t.startswith("작성일")
            ]
            proj_left = min((bb[0] for _, bb in lines), default=None)
            gap = round(proj_left - img[2], 2) if img and proj_left is not None else None
            report["project_cases"][key] = {
                **{k: case[k] for k in ("input_len", "run_error", "font_pt", "ends_with_ellipsis", "total_len")},
                "logo_kept": case["left_header"] == "&G" and bool(detail["header_logo"]),
                "project_lines": [t for t, _ in lines],
                "header_image_right_mm": img[2] if img else None,
                "project_left_mm": proj_left,
                "gap_mm": gap,
                "no_overlap": gap is not None and gap >= MIN_GAP_MM,
            }
    report["png"] = {
        name: render(out / f"{name}.pdf", out)
        for name in ["fit", "multi", "beforeprint", "nodate"] + [f"name_{k}" for k in rec.get("project_cases", {})]
    }
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="구조계산서 양식 PDF 실측 검증")
    p.add_argument("--xlsm", type=Path, default=DEFAULT_OUT)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)

    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    work = out / "verify_work.xlsm"
    shutil.copyfile(args.xlsm, work)
    with ExcelSession() as session:
        rec = run_excel(session.xl, work, out)
    report = analyze(out, rec)
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    emit(json.dumps(report, ensure_ascii=False, indent=2))  # cp949 로 리디렉션해도 멈추지 않게
    return 0


if __name__ == "__main__":
    sys.exit(main())
