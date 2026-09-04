# add2.py — 2-digit integer addition CLI

Adds two 2-digit positive integers given as command-line arguments. Python 3.8+,
standard library only, no external dependencies.

## Usage

```
python add2.py <a> <b>
```

Both operands must be 2-digit integers in the range **10-99** (inclusive).
Surrounding whitespace is stripped before parsing. On success the sum is printed
to stdout as `A + B = C` (the sum itself has no digit limit, e.g. `99 + 99 = 198`).
Errors are written to stderr as a single line: `Error: <reason>` for a bad
operand, or `Usage: ...` for the wrong number of arguments.

## Example

```
$ python add2.py 12 34
12 + 34 = 46
```

## "2-digit" definition

| Input        | Result                                          |
|--------------|-------------------------------------------------|
| `10` – `99`  | accepted                                         |
| `9`, `100`   | rejected — not a 2-digit number (must be 10-99)  |
| `-30`, `+12` | rejected — not an integer                        |
| `07`         | parsed as `7`, then rejected — out of range      |
| `  42  `     | accepted — surrounding whitespace is stripped    |

## Exit codes

| Code | Meaning                                                          |
|------|----------------------------------------------------------------- |
| 0    | success                                                          |
| 1    | operand error (not an integer, out of range, negative, empty)    |
| 2    | wrong number of arguments (exactly 2 required)                   |

## Tests

```
python -m unittest
```
