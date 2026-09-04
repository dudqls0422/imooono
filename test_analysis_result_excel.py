"""`해석결과 확인_EX.py` 테스트.

파일명에 공백이 있어 import 문으로 못 불러오므로 importlib 로 로드한다.
실행: python -m unittest

레이아웃: build_result_excel 은 이미지당 워크시트 1개(탭 "01".."NN"), 페이지나눔·캡션 셀 없음,
성공 시트는 이미지만, 실패 시트는 A1 에 "[캡처 실패] <캡션>".
"""
import contextlib
import hashlib
import importlib.util
import io
import math
import os
import re
import shutil
import tempfile
import unittest
from unittest import mock

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string
from PIL import Image as PILImage

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_PATH = os.path.join(HERE, "해석결과 확인_EX.py")
ORIGINAL_PATH = os.path.join(HERE, "해석결과 확인.py")
DESKTOP_ORIGINAL = r"C:\Users\KYB\Desktop\해석결과 캡쳐\해석결과 확인.py"


def load_module():
    spec = importlib.util.spec_from_file_location("analysis_result_ex", MOD_PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


mod = load_module()


def make_jpg(path, size=(1280, 768), color=(200, 120, 60)):
    PILImage.new("RGB", size, color).save(path, "JPEG")


def all_texts(wb):
    """통합 문서 전 시트의 값 있는 셀 텍스트를 리스트로."""
    out = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if c.value is not None:
                    out.append(str(c.value))
    return out


def _sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TmpMixin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="test_arex_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self._saved = {k: getattr(mod, k) for k in
                       ("EXPORT_DIR", "MATERIAL", "INCLUDE_TRUSS_FORCE", "headers")}
        self.addCleanup(self._restore)

    def _restore(self):
        for k, v in self._saved.items():
            setattr(mod, k, v)

    @contextlib.contextmanager
    def mock_requests(self, fail_capture_indices=()):
        """requests.post/put 를 목으로. CAPTURE 는 EXPORT_PATH 에 실제 jpg 를 써서
        '캡처가 파일을 만든 것'처럼 흉내낸다. fail_capture_indices 의 순번은 비200 처리."""
        state = {"cap": 0}

        def post(url, headers=None, json=None, **kw):
            resp = mock.Mock()
            resp.text = "{}"
            resp.json = lambda: {}
            if url.endswith("/view/CAPTURE"):
                idx = state["cap"]
                state["cap"] += 1
                if idx in fail_capture_indices:
                    resp.status_code = 500
                else:
                    resp.status_code = 200
                    make_jpg(json["Argument"]["EXPORT_PATH"])
            else:
                resp.status_code = 200
            return resp

        def put(url, headers=None, json=None, **kw):
            resp = mock.Mock()
            resp.status_code = 200
            resp.text = "{}"
            return resp

        with mock.patch.object(mod, "requests") as m:
            m.post.side_effect = post
            m.put.side_effect = put
            yield m

    def run_main_with_export_dir(self, export_dir, **mock_kw):
        mod.EXPORT_DIR = export_dir
        mod.MATERIAL = "STL"
        mod.INCLUDE_TRUSS_FORCE = True
        mod.headers = {"Content-Type": "application/json", "MAPI-Key": "dummy"}
        with self.mock_requests(**mock_kw), \
                mock.patch.object(mod, "messagebox"), \
                mock.patch.object(mod.os, "startfile", create=True):
            mod.main()


# ---------------------------------------------------------------------------
# build_result_excel — 이미지당 시트 1개 레이아웃 (1-10)
# ---------------------------------------------------------------------------
class BuildResultExcelTests(TmpMixin):
    def _jpg(self, name="a.jpg", size=(1280, 768)):
        p = os.path.join(self.tmp, name)
        make_jpg(p, size=size)
        return p

    def _build(self, items, name="out.xlsx"):
        out = os.path.join(self.tmp, name)
        mod.build_result_excel(items, out, "STL")
        return load_workbook(out)

    def test_01_one_sheet_per_item(self):
        p = self._jpg()
        for n in (15, 14):
            wb = self._build([(p, f"c{i}") for i in range(n)], f"out{n}.xlsx")
            self.assertEqual(len(wb.worksheets), n)

    def test_02_all_sheets_landscape_a4_fit_1x1(self):
        p = self._jpg()
        wb = self._build([(p, "c0"), (p, "c1"), (None, "c2")])
        for ws in wb.worksheets:
            self.assertEqual(ws.page_setup.orientation, "landscape")
            self.assertEqual(int(ws.page_setup.paperSize), 9)
            self.assertTrue(ws.sheet_properties.pageSetUpPr.fitToPage)
            self.assertEqual(int(ws.page_setup.fitToWidth), 1)
            self.assertEqual(int(ws.page_setup.fitToHeight), 1)

    def test_03_no_page_breaks(self):
        p = self._jpg()
        wb = self._build([(p, "c0"), (p, "c1")])
        for ws in wb.worksheets:
            self.assertEqual(len(ws.row_breaks), 0)
            self.assertEqual(len(ws.col_breaks), 0)

    def test_04_success_sheet_has_no_text(self):
        p = self._jpg()
        wb = self._build([(p, "c0"), (p, "c1")])
        for ws in wb.worksheets:
            vals = [c.value for row in ws.iter_rows() for c in row if c.value is not None]
            self.assertEqual(vals, [])

    def test_05_image_count_per_sheet(self):
        p = self._jpg()
        wb = self._build([(p, "ok"), (None, "fail")])
        self.assertEqual(len(wb.worksheets[0]._images), 1)
        self.assertEqual(len(wb.worksheets[1]._images), 0)

    def test_06_image_aspect_ratio_preserved(self):
        p = self._jpg(size=(1280, 768))
        wb = self._build([(p, "c0")])
        img = wb.worksheets[0]._images[0]
        self.assertLess(abs(img.width / img.height - 1280 / 768), 0.02)

    def test_07_failure_sheet_a1_text_and_color(self):
        p = self._jpg()
        cap = "가새 인장력(ENV_STR)"
        wb = self._build([(p, "ok"), (None, cap)])
        ws = wb.worksheets[1]
        self.assertEqual(len(ws._images), 0)
        self.assertTrue(ws["A1"].value.startswith("[캡처 실패]"))
        self.assertIn(cap, ws["A1"].value)
        self.assertEqual(ws["A1"].font.color.rgb, "FFFF0000")

    def test_08_mixed_real_none_missing_keeps_order(self):
        real = self._jpg()
        missing = os.path.join(self.tmp, "does_not_exist.jpg")
        wb = self._build([(real, "01c"), (None, "02c"), (missing, "03c")])
        self.assertEqual([ws.title for ws in wb.worksheets], ["01", "02", "03"])
        self.assertEqual(len(wb.worksheets[0]._images), 1)
        self.assertEqual(len(wb.worksheets[1]._images), 0)
        self.assertEqual(len(wb.worksheets[2]._images), 0)
        self.assertTrue(wb.worksheets[2]["A1"].value.startswith("[캡처 실패]"))

    def test_09_empty_items_raises(self):
        with self.assertRaises(ValueError):
            mod.build_result_excel([], os.path.join(self.tmp, "x.xlsx"), "STL")

    def test_10_tab_names_format_unique_len(self):
        p = self._jpg()
        wb = self._build([(p, f"c{i}") for i in range(12)])
        titles = [ws.title for ws in wb.worksheets]
        self.assertEqual(titles, [f"{i + 1:02d}" for i in range(12)])
        self.assertEqual(len(set(titles)), len(titles))
        for t in titles:
            self.assertLessEqual(len(t), 31)


def _parse_range_end(area):
    """print_area 문자열(예 "'01'!$A$1:$T$36" / "A1:T36")에서 끝 셀 (열idx, 행) 추출."""
    s = area if isinstance(area, str) else (area[0] if area else "")
    s = s.replace("$", "")
    if "!" in s:
        s = s.split("!", 1)[1]
    m = re.search(r":([A-Za-z]+)(\d+)$", s)
    if not m:
        m = re.match(r"^([A-Za-z]+)(\d+)$", s)  # 단일 셀
    assert m, f"print_area 파싱 실패: {area!r}"
    return column_index_from_string(m.group(1)), int(m.group(2))


# ---------------------------------------------------------------------------
# 인쇄 중앙정렬 (A4 정중앙 배치)
# ---------------------------------------------------------------------------
class PrintCenteringTests(TmpMixin):
    def _jpg(self, name="a.jpg", size=(1280, 768)):
        p = os.path.join(self.tmp, name)
        make_jpg(p, size=size)
        return p

    def _build(self, items, name="out.xlsx"):
        out = os.path.join(self.tmp, name)
        mod.build_result_excel(items, out, "STL")
        return load_workbook(out)

    def test_all_sheets_centered_both_axes(self):
        p = self._jpg()
        wb = self._build([(p, "c0"), (p, "c1"), (None, "실패")])
        for ws in wb.worksheets:
            self.assertIs(ws.print_options.horizontalCentered, True)
            self.assertIs(ws.print_options.verticalCentered, True)

    def test_success_sheet_print_area_covers_image(self):
        p = self._jpg(size=(1280, 768))
        wb = self._build([(p, "c0")])
        ws = wb.worksheets[0]
        self.assertTrue(ws._images)
        # 풋프린트는 스케일된 이미지 크기(1180px 폭, 1280:768 비율) 기준으로 계산됨.
        # (재로드된 img.width/height 는 원본 native 1280x768 이라 기준으로 쓰지 않는다.)
        scaled_w = 1180
        scaled_h = round(scaled_w * 768 / 1280)  # 708
        min_cols = math.ceil(scaled_w / 64)      # 19
        min_rows = math.ceil(scaled_h / 20)      # 36
        end_col, end_row = _parse_range_end(ws.print_area)
        self.assertGreaterEqual(end_col, min_cols)
        self.assertGreaterEqual(end_row, min_rows)
        self.assertLessEqual(end_col, min_cols + 3)
        self.assertLessEqual(end_row, min_rows + 3)
        # 시작이 A1 인지
        norm = (ws.print_area if isinstance(ws.print_area, str)
                else ws.print_area[0]).replace("$", "")
        self.assertIn("A1", norm)

    def test_failure_sheet_a1_centered(self):
        p = self._jpg()
        cap = "가새 인장력(ENV_STR)"
        wb = self._build([(p, "ok"), (None, cap)])
        ws = wb.worksheets[1]
        self.assertEqual(len(ws._images), 0)
        self.assertTrue(ws["A1"].value.startswith("[캡처 실패]"))
        self.assertEqual(ws["A1"].font.color.rgb, "FFFF0000")
        self.assertEqual(ws["A1"].alignment.horizontal, "center")
        self.assertEqual(ws["A1"].alignment.vertical, "center")

    def test_centering_does_not_break_page_setup(self):
        p = self._jpg()
        wb = self._build([(p, "c0"), (None, "c1")])
        for ws in wb.worksheets:
            self.assertEqual(int(ws.page_setup.paperSize), 9)
            self.assertEqual(ws.page_setup.orientation, "landscape")
            self.assertEqual(int(ws.page_setup.fitToWidth), 1)
            self.assertEqual(int(ws.page_setup.fitToHeight), 1)
            self.assertEqual(len(ws.row_breaks), 0)
        # 성공 시트 셀 텍스트 0 유지
        vals = [c.value for row in wb.worksheets[0].iter_rows()
                for c in row if c.value is not None]
        self.assertEqual(vals, [])

    def test_bytesio_roundtrip_keeps_centered_and_margins(self):
        p = self._jpg()
        out = os.path.join(self.tmp, "rt.xlsx")
        mod.build_result_excel([(p, "c0"), (None, "c1")], out, "STL")
        with open(out, "rb") as f:
            buf = io.BytesIO(f.read())
        wb = load_workbook(buf)
        for ws in wb.worksheets:
            self.assertIs(ws.print_options.horizontalCentered, True)
            self.assertIs(ws.print_options.verticalCentered, True)
            self.assertEqual(ws.page_margins.left, 0.5)
            self.assertEqual(ws.page_margins.right, 0.5)
            self.assertEqual(ws.page_margins.top, 0.5)
            self.assertEqual(ws.page_margins.bottom, 0.5)
            self.assertEqual(ws.page_margins.header, 0.2)
            self.assertEqual(ws.page_margins.footer, 0.2)


# ---------------------------------------------------------------------------
# build_steps / main 통합 (회귀)
# ---------------------------------------------------------------------------
class StepsAndMainTests(TmpMixin):
    def test_build_steps_include_truss(self):
        steps = mod.build_steps(True)
        self.assertEqual(len(steps), 15)
        self.assertIn(mod.TRUSS_FORCE, steps)

    def test_build_steps_exclude_truss(self):
        steps = mod.build_steps(False)
        self.assertEqual(len(steps), 14)
        self.assertNotIn(mod.TRUSS_FORCE, steps)

    def test_main_leaves_only_xlsx_in_export_dir(self):
        d = os.path.join(self.tmp, "export")
        os.makedirs(d)
        for i in range(1, 4):
            make_jpg(os.path.join(d, f"model_{i:03d}.jpg"))
        existing = sorted(f for f in os.listdir(d) if f.startswith("model_"))

        self.run_main_with_export_dir(d)

        files = os.listdir(d)
        new_jpgs = [f for f in files if f.lower().endswith(".jpg") and f not in existing]
        self.assertEqual(new_jpgs, [])
        self.assertIn(mod.RESULT_XLSX_NAME, files)
        still = sorted(f for f in os.listdir(d) if f.startswith("model_"))
        self.assertEqual(still, existing)

    def test_main_removes_tempdir_on_success(self):
        d = os.path.join(self.tmp, "export_ok")
        os.makedirs(d)
        created = {}
        real_mkdtemp = tempfile.mkdtemp

        def rec(*a, **k):
            p = real_mkdtemp(*a, **k)
            created["p"] = p
            return p

        with mock.patch.object(mod.tempfile, "mkdtemp", side_effect=rec):
            self.run_main_with_export_dir(d)
        self.assertIn("p", created)
        self.assertFalse(os.path.exists(created["p"]))

    def test_main_removes_tempdir_when_excel_fails(self):
        d = os.path.join(self.tmp, "export_err")
        os.makedirs(d)
        created = {}
        real_mkdtemp = tempfile.mkdtemp

        def rec(*a, **k):
            p = real_mkdtemp(*a, **k)
            created["p"] = p
            return p

        mod.EXPORT_DIR = d
        mod.MATERIAL = "STL"
        mod.INCLUDE_TRUSS_FORCE = True
        mod.headers = {"MAPI-Key": "dummy"}
        with mock.patch.object(mod.tempfile, "mkdtemp", side_effect=rec), \
                mock.patch.object(mod, "build_result_excel", side_effect=RuntimeError("boom")), \
                self.mock_requests(), \
                mock.patch.object(mod, "messagebox"), \
                mock.patch.object(mod.os, "startfile", create=True):
            with self.assertRaises(RuntimeError):
                mod.main()
        self.assertFalse(os.path.exists(created["p"]))

    def test_one_capture_non200_placeholder_rest_ok(self):
        d = os.path.join(self.tmp, "export_partial")
        os.makedirs(d)
        self.run_main_with_export_dir(d, fail_capture_indices=(2,))
        out = os.path.join(d, mod.RESULT_XLSX_NAME)
        self.assertTrue(os.path.exists(out))
        wb = load_workbook(out)
        self.assertEqual(len(wb.worksheets), 15)
        texts = all_texts(wb)
        self.assertTrue(any(t.startswith("[캡처 실패]") for t in texts))
        total_images = sum(len(ws._images) for ws in wb.worksheets)
        self.assertEqual(total_images, 14)

    def test_step_exception_uses_human_caption_not_funcname(self):
        """스텝이 캡션 반환 전 예외로 죽어도 실패 시트 A1 엔 사람이 읽는 한글 캡션이 들어가고
        bare 함수명(TRUSS_FORCE 등)은 어느 셀에도 없어야 한다."""

        def boom(export_path):
            raise RuntimeError("simulated step failure")

        boom.__name__ = "TRUSS_FORCE"

        d = os.path.join(self.tmp, "export_exc")
        os.makedirs(d)
        mod.EXPORT_DIR = d
        mod.MATERIAL = "STL"
        mod.INCLUDE_TRUSS_FORCE = True
        mod.headers = {"MAPI-Key": "dummy"}
        with mock.patch.object(mod, "TRUSS_FORCE", boom), \
                self.mock_requests(), \
                mock.patch.object(mod, "messagebox"), \
                mock.patch.object(mod.os, "startfile", create=True):
            mod.main()

        wb = load_workbook(os.path.join(d, mod.RESULT_XLSX_NAME))
        texts = all_texts(wb)
        self.assertIn("[캡처 실패] 가새 인장력(ENV_STR)", texts)
        joined = " || ".join(texts)
        for funcname in mod.STEP_CAPTIONS:
            self.assertNotIn(funcname, joined)


# ---------------------------------------------------------------------------
# 원본 무변경 확인
# ---------------------------------------------------------------------------
class OriginalUntouchedTests(unittest.TestCase):
    def test_repo_original_matches_desktop_original(self):
        self.assertTrue(os.path.exists(ORIGINAL_PATH))
        if os.path.exists(DESKTOP_ORIGINAL):
            self.assertEqual(_sha(ORIGINAL_PATH), _sha(DESKTOP_ORIGINAL))

    def test_original_has_no_excel_code(self):
        with open(ORIGINAL_PATH, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("openpyxl", src)
        self.assertNotIn("build_result_excel", src)


if __name__ == "__main__":
    unittest.main()
