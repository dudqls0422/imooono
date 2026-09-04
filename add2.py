#!/usr/bin/env python3
"""Add two 2-digit positive integers passed as command-line arguments.

Usage:
    python add2.py <a> <b>

Both operands must be 2-digit integers in the range 10-99 (inclusive). On
success the sum is printed to stdout as ``A + B = C``; the sum itself has no
digit limit. On error a single ``Error: ...`` or ``Usage: ...`` line is written
to stderr and the process exits non-zero. Standard library only.
"""
import re
import sys

# A valid operand (after stripping) is a run of ASCII digits: no sign, no
# decimal point, no internal whitespace.
_INTEGER_RE = re.compile(r"^\d+$")

USAGE = "Usage: python add2.py <a> <b>   (each a 2-digit integer, 10-99)"


def parse_operand(raw: str, position: int) -> int:
    """Parse and validate a single operand.

    Strips surrounding whitespace, requires the result to match ``^\\d+$``,
    converts to ``int``, and checks the 10-99 range. Raises ``ValueError`` with
    a human-readable message on any failure. Pure function.
    """
    text = raw.strip()
    if not text:
        raise ValueError("operand {} is empty".format(position))
    if not _INTEGER_RE.match(text):
        raise ValueError(
            "operand {} is not an integer: '{}'".format(position, raw)
        )
    value = int(text)
    if not 10 <= value <= 99:
        raise ValueError(
            "operand {} is not a 2-digit number (must be 10-99): {}".format(
                position, value
            )
        )
    return value


def add(a: int, b: int) -> int:
    """Return the sum of two integers. Pure function."""
    return a + b


def main(argv) -> int:
    """Run the CLI. Returns the process exit code (0 ok / 1 operand / 2 args)."""
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        a = parse_operand(argv[0], 1)
        b = parse_operand(argv[1], 2)
    except ValueError as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 1
    print("{} + {} = {}".format(a, b, add(a, b)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
