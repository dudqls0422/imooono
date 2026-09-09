"""템플릿 파싱 + 검증(거부/경고) 규칙."""
from __future__ import annotations

import pytest
from openpyxl import Workbook

from tools.portal_frame_gen.template import (HEADERS, TemplateError,
                                             read_template, validate,
                                             write_template)

from .conftest import make_params


def test_valid_params_pass():
    assert validate(make_params()) is not None


@pytest.mark.parametrize("over", [
    {"span_m": 0}, {"span_m": -1}, {"eave_height_m": 0}, {"eave_height_m": -2},
    {"bay_count": 0}, {"bay_spacing_m": 0}, {"bay_spacing_m": -3},
    {"pitch_rise": 0}, {"pitch_run": 0},
    {"base_fixity": "roller"}, {"frame_mode": "1D"},
])
def test_reject_rules(over):
    with pytest.raises(TemplateError):
        validate(make_params(**over))


def test_warn_steep_roof_30_to_45():
    p = make_params(pitch_rise=1.0, pitch_run=1.5)  # ~33.7°
    validate(p)
    assert p.warnings and "경사각" in p.warnings[0]


def test_reject_roof_over_45():
    with pytest.raises(TemplateError):
        validate(make_params(pitch_rise=1.0, pitch_run=0.8))  # ~51°


def test_roof_angle_deg_takes_precedence():
    p = make_params(roof_angle_deg=10.0, pitch_rise=99.0, pitch_run=1.0)
    validate(p)
    assert abs(p.roof_angle() - 10.0) < 1e-9


# --- xlsx 왕복 / 리더 -----------------------------------------------------
def _write_xlsx(path, header, row):
    wb = Workbook()
    ws = wb.active
    ws.append(header)
    ws.append(row)
    wb.save(path)


def test_make_template_roundtrip(tmp_path):
    f = tmp_path / "t.xlsx"
    write_template(str(f))
    p = read_template(str(f))
    assert p.span_m == 20.0 and p.frame_mode == "3D" and p.material_name == "SS275"
    assert p.column_section == "H-400x200x8x13"


def test_reader_missing_header(tmp_path):
    f = tmp_path / "t.xlsx"
    bad = [h for h in HEADERS if h != "material_name"]
    _write_xlsx(f, bad, [1] * len(bad))
    with pytest.raises(TemplateError):
        read_template(str(f))


def test_reader_missing_section_name(tmp_path):
    f = tmp_path / "t.xlsx"
    row = [20, 6, 1, 10, None, 5, 6, 0, "", "H-350", "H-200", "SS275",
           "pinned", "3D"]
    _write_xlsx(f, HEADERS, row)
    with pytest.raises(TemplateError):
        read_template(str(f))


def test_reader_bay_spacing_list_wrong_length(tmp_path):
    f = tmp_path / "t.xlsx"
    row = [20, 6, 1, 10, None, 5, "6,6,6", 0, "H-A", "H-B", "H-C", "SS275",
           "pinned", "3D"]
    _write_xlsx(f, HEADERS, row)
    with pytest.raises(TemplateError):
        read_template(str(f))


def test_reader_bay_spacing_list_ok(tmp_path):
    f = tmp_path / "t.xlsx"
    row = [20, 6, 1, 10, None, 5, "6,6,6,6,6", 0, "H-A", "H-B", "H-C", "SS275",
           "pinned", "3D"]
    _write_xlsx(f, HEADERS, row)
    p = read_template(str(f))
    assert p.bay_spacing_m == 6.0
