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

---

# 해석결과 확인_EX.py — MIDAS 캡처 결과 Excel 정리

`해석결과 확인.py`(원본, 무변경 보존)를 확장해, MIDAS Gen NX `/view/CAPTURE` 로 받은
해석결과 캡처들을 하나의 Excel(`해석결과 확인_EX.xlsx`)로 정리한다. GUI 에서 MAPI-Key /
재질(STL·RC) / "가새 인장력(브레이스) 캡처 포함" 여부를 입력받는다.

```
pip install -r requirements.txt
python "해석결과 확인_EX.py"
```

## 인쇄 주의

결과 Excel 은 **이미지당 워크시트 1개**로 구성된다(탭 `01`, `02`, …). 캡션·설명 텍스트는
넣지 않으며, 캡처에 실패한 스텝만 그 시트 `A1` 에 빨간 `[캡처 실패] <설명>` 을 표시한다.
각 시트는 가로 A4 1페이지로 맞춰져 있다(빈 페이지 없음).

- **전부 인쇄하려면 인쇄 대화상자에서 '전체 통합 문서(Entire Workbook)' 를 선택할 것.**
- '활성 시트만' 을 인쇄하면 **1장만** 나온다.

## 산출 위치

캡처 JPG 는 `EXPORT_DIR`(`C:\Users\KYB\Desktop\해석결과 캡쳐`) 밖 임시폴더에 만들어 Excel 에
임베드한 뒤 삭제한다. `EXPORT_DIR` 에는 최종 `.xlsx` 만 추가되고, 기존 `model_*.jpg` 는
건드리지 않는다.
