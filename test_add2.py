"""Tests for add2.py — the 17 cases specified by Plan.

Run with:  python -m unittest
"""
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from add2 import add, main, parse_operand


class AddTests(unittest.TestCase):
    def test_add_min(self):  # (1)
        self.assertEqual(add(10, 10), 20)

    def test_add_max(self):  # (2)
        self.assertEqual(add(99, 99), 198)

    def test_add_mixed(self):  # (3)
        self.assertEqual(add(42, 17), 59)


class ParseOperandTests(unittest.TestCase):
    def test_plain(self):  # (4)
        self.assertEqual(parse_operand("12", 1), 12)

    def test_surrounding_whitespace(self):  # (5)
        self.assertEqual(parse_operand("  34  ", 2), 34)

    def test_below_range(self):  # (6)
        with self.assertRaises(ValueError):
            parse_operand("9", 1)

    def test_above_range(self):  # (7)
        with self.assertRaises(ValueError):
            parse_operand("100", 1)

    def test_non_digit(self):  # (8)
        with self.assertRaises(ValueError):
            parse_operand("1a", 1)

    def test_empty(self):  # (9)
        with self.assertRaises(ValueError):
            parse_operand("", 1)

    def test_negative(self):  # (10)
        with self.assertRaises(ValueError):
            parse_operand("-30", 1)

    def test_leading_zero(self):  # (11)
        with self.assertRaises(ValueError):
            parse_operand("07", 1)


class MainTests(unittest.TestCase):
    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_ok(self):  # (12)
        code, out, err = self._run(["12", "34"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "12 + 34 = 46\n")

    def test_ok_max(self):  # (13)
        code, out, err = self._run(["99", "99"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "99 + 99 = 198\n")

    def test_operand_out_of_range(self):  # (14)
        code, out, err = self._run(["9", "10"])
        self.assertEqual(code, 1)
        self.assertIn("Error:", err)

    def test_operand_not_integer(self):  # (15)
        code, out, err = self._run(["1a", "20"])
        self.assertEqual(code, 1)

    def test_too_few_args(self):  # (16)
        code, out, err = self._run(["12"])
        self.assertEqual(code, 2)
        self.assertIn("Usage:", err)

    def test_too_many_args(self):  # (17)
        code, out, err = self._run(["1", "2", "3"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
