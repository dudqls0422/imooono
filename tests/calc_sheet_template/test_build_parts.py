"""구조계산서 양식 생성기 — Excel 없이 확인할 수 있는 부분(로고·바닥글 이미지·VBA 원본·AccessVBOM 판정)."""
from __future__ import annotations

import hashlib

import pytest
from PIL import Image

from tools.calc_sheet_template import build_template as bt


def _make_ico(path, sizes=(16, 32, 48, 128)):
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    for y in range(20, 108):
        for x in range(30, 98):
            img.putpixel((x, y), (120, 120, 120, 255))
    img.save(path, format="ICO", sizes=[(s, s) for s in sizes])
    return path


# ---------------------------------------------------------------- 로고


def test_ico_picks_128_frame_and_keeps_alpha(tmp_path):
    img = bt.load_logo_image(_make_ico(tmp_path / "logo.ico"))
    assert img.size == (128, 128)
    assert img.mode == "RGBA"
    assert img.getpixel((0, 0))[3] == 0  # 투명 배경 유지


def test_ico_without_128_uses_largest_without_upscaling(tmp_path):
    assert bt.load_logo_image(_make_ico(tmp_path / "small.ico", sizes=(16, 48))).size == (48, 48)


def test_source_logo_is_not_modified(tmp_path):
    ico = _make_ico(tmp_path / "logo.ico")
    before = hashlib.sha256(ico.read_bytes()).hexdigest()
    mtime = ico.stat().st_mtime_ns
    bt.resolve_logo(ico, tmp_path / "assets")
    assert hashlib.sha256(ico.read_bytes()).hexdigest() == before
    assert ico.stat().st_mtime_ns == mtime


def test_resolve_logo_from_source_writes_png(tmp_path):
    png, origin = bt.resolve_logo(_make_ico(tmp_path / "logo.ico"), tmp_path / "assets")
    assert origin == "source"
    assert png == tmp_path / "assets" / "logo.png"
    with Image.open(png) as img:
        assert img.format == "PNG" and img.size == (128, 128)


def test_resolve_logo_falls_back_to_cached_png_with_warning(tmp_path, capsys):
    assets = tmp_path / "assets"
    assets.mkdir()
    Image.new("RGBA", (128, 128)).save(assets / "logo.png")
    png, origin = bt.resolve_logo(tmp_path / "없는파일.ico", assets)
    assert (png, origin) == (assets / "logo.png", "cached")
    err = capsys.readouterr().err
    assert "[경고]" in err and "없는파일.ico" in err


def test_resolve_logo_falls_back_to_placeholder_with_warning(tmp_path, capsys):
    assets = tmp_path / "assets"
    png, origin = bt.resolve_logo(tmp_path / "없는파일.ico", assets)
    assert origin == "placeholder"
    assert png == assets / "logo_placeholder.png" and png.exists()
    assert "자리표시" in capsys.readouterr().err


def test_repo_assets_exist():
    for name in ("logo.png", "logo_placeholder.png", "footer.png"):
        assert (bt.ASSETS / name).exists(), name
    with Image.open(bt.ASSETS / "logo.png") as img:
        assert img.size == (128, 128) and img.mode == "RGBA"


# ---------------------------------------------------------------- 바닥글 합성


@pytest.mark.parametrize("width_mm", [180.0, 174.1])
def test_footer_width_follows_body_width_at_300dpi(tmp_path, width_mm):
    png, _ = bt.resolve_logo(_make_ico(tmp_path / "logo.ico"), tmp_path / "assets")
    out = bt.compose_footer(png, tmp_path / "footer.png", width_mm=width_mm)
    with Image.open(out) as img:
        assert img.width == round(width_mm / 25.4 * 300)
        assert round(img.info["dpi"][0]) == 300
        # 맨 위는 굵은 회색 가로선이 양 끝까지
        assert img.getpixel((0, 2)) == bt.RULE_RGB
        assert img.getpixel((img.width - 1, 2)) == bt.RULE_RGB
        assert img.height >= bt.mm_to_px(bt.FOOTER_LOGO_MM) + bt.mm_to_px(bt.RULE_MM)


def test_footer_changes_when_logo_changes(tmp_path):
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    Image.new("RGBA", (128, 128), (255, 0, 0, 255)).save(a)
    Image.new("RGBA", (128, 128), (0, 0, 255, 255)).save(b)
    assert bt.compose_footer(a, tmp_path / "fa.png").read_bytes() != bt.compose_footer(b, tmp_path / "fb.png").read_bytes()


def test_footer_logo_is_downscaled_to_5mm_keeping_ratio(tmp_path):
    logo = tmp_path / "wide.png"
    Image.new("RGBA", (256, 128), (255, 0, 0, 255)).save(logo)  # 2:1
    with Image.open(bt.compose_footer(logo, tmp_path / "f.png")) as img:
        h = bt.mm_to_px(bt.FOOTER_LOGO_MM)
        row = img.height - bt.mm_to_px(0.4) - h // 2
        reds = [x for x in range(0, 300) if img.getpixel((x, row))[0] > 200 and img.getpixel((x, row))[2] < 60]
        assert abs(len(reds) - 2 * h) <= 1


def test_footer_does_not_upscale_small_logo(tmp_path):
    small = tmp_path / "s.png"
    Image.new("RGBA", (20, 20), (255, 0, 0, 255)).save(small)
    with Image.open(bt.compose_footer(small, tmp_path / "f.png")) as img:
        reds = [x for x in range(0, 80) if img.getpixel((x, img.height // 2 + 5))[:3] == (255, 0, 0)]
        assert len(reds) == 20  # 20px 그대로, 늘리지 않음


# ---------------------------------------------------------------- VBA 원본


def test_vba_sources_contract():
    src = bt.load_vba_sources()
    bas = src.header_sync_bas
    assert bas.startswith('Attribute VB_Name = "HeaderSync"')
    assert "Public Sub UpdateHeaders()" in bas
    assert 'Replace(SingleLine(s), "&", "&&")' in bas
    # 머리글 텍스트는 PrintCommunication=True 상태에서 넣는다(False 일괄 반영은 긴 한글에서 로고까지 지워짐, 실측)
    assert "Application.PrintCommunication = False" not in bas
    assert "Application.PrintCommunication = True" in bas
    assert ".LeftHeader" not in bas and "Footer" not in bas  # 로고(&G)·바닥글은 건드리지 않음
    assert "MAX_HEADER_LEN As Long = 255" in bas and 'ELLIPSIS As String = "…"' in bas
    # 255자 제한은 머리글 전체(&L 왼쪽 &C 가운데 &R 오른쪽) 기준 (실측: 256자부터 구역이 뒤섞여 로고가 지워짐)
    assert 'MAX_HEADER_LEN - Len("&L" & LEFT_HEADER & "&C" & "&R")' in bas
    # D4-2: 가운데는 비우고, 프로젝트명 글꼴은 9 → 8 → 7pt
    assert 'ws.PageSetup.CenterHeader = ""' in bas
    for name in ("CAP_9PT", "CAP_8PT", "CAP_7PT", "ASCII_WEIGHT"):
        assert f"Private Const {name} As Double = " in bas
    assert "Workbook_Open" in src.this_workbook and "Workbook_BeforePrint" in src.this_workbook
    assert "Worksheet_Change" in src.settings_sheet
    assert "PROJECT_NAME" in src.settings_sheet and "DOC_DATE" in src.settings_sheet


def test_vba_encodes_to_ansi_codepage():
    for text in bt.load_vba_sources().__dict__.values():
        bt.to_crlf(text).encode("mbcs")  # 한국어 Windows(CP949)에서 깨지지 않아야 함("…" 포함)


def test_inject_vba_constants_replaces_measured_values():
    src = bt.load_vba_sources().header_sync_bas
    text = {"caps": {9: 27.3, 8: 31.1, 7: 35.6}, "ascii_weight": 0.55}
    out = bt.inject_vba_constants(src, text)
    assert "Private Const CAP_9PT As Double = 27.30" in out
    assert "Private Const CAP_8PT As Double = 31.10" in out
    assert "Private Const CAP_7PT As Double = 35.60" in out
    assert "Private Const ASCII_WEIGHT As Double = 0.55" in out
    assert out.count("\n") == src.count("\n")  # 다른 줄은 그대로


def test_inject_vba_constants_fails_loudly_when_constant_missing():
    with pytest.raises(RuntimeError):
        bt.inject_vba_constants("Option Explicit\n", {"caps": {9: 1, 8: 1, 7: 1}, "ascii_weight": 0.5})


def test_header_image_is_logo_plus_title_10mm_at_300dpi(tmp_path):
    png, _ = bt.resolve_logo(_make_ico(tmp_path / "logo.ico"), tmp_path / "assets")
    out = bt.compose_header(png, tmp_path / "header.png")
    with Image.open(out) as img:
        assert img.height == bt.mm_to_px(bt.HEADER_LOGO_MM)  # 118px = 10mm@300dpi (128px 에서 줄임)
        assert round(img.info["dpi"][0]) == 300
        # 로고(정사각) 오른쪽에 문서명이 있어 가로가 훨씬 길다 (9pt 문서명 약 64mm)
        assert 60 < img.width / 300 * 25.4 < 85
        # 문서명 영역에 검은 글자가 있다
        assert any(img.getpixel((x, img.height // 2))[:3] == (0, 0, 0) for x in range(img.height + 30, img.width))


def test_settings_notes_mention_limit():
    notes = bt.settings_notes(35)
    assert any("35자 이내" in n and "자동으로 작아집니다" in n for n in notes)


def test_to_crlf():
    assert bt.to_crlf("a\nb\r\nc") == "a\r\nb\r\nc"


# ---------------------------------------------------------------- AccessVBOM 판정 (읽기 전용)


def test_effective_access_vbom_policy_wins():
    vals = {"HKCU\\Policies": 0, "HKLM\\Policies": None, "HKCU": 1, "HKLM": None}
    assert bt.effective_access_vbom(vals) == 0


def test_effective_access_vbom_missing_is_off():
    assert bt.effective_access_vbom(dict.fromkeys(bt.VBOM_PLACES)) == 0


def test_effective_access_vbom_user_on():
    vals = {"HKCU\\Policies": None, "HKLM\\Policies": None, "HKCU": 1, "HKLM": None}
    assert bt.effective_access_vbom(vals) == 1


def test_build_module_never_writes_registry():
    text = (bt.HERE / "build_template.py").read_text(encoding="utf-8")
    for forbidden in ("SetValueEx", "CreateKey", "DeleteValue", "KEY_WRITE", "KEY_SET_VALUE"):
        assert forbidden not in text


def test_logo_path_only_as_cli_default():
    text = (bt.HERE / "build_template.py").read_text(encoding="utf-8")
    assert text.count("SNP FILE STATION.ico") == 1
    assert not hasattr(bt, "DEFAULT_LOGO")
