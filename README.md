# imooono

MIDAS Gen NX Open API 기반 Python 구조해석 자동화 프로그램입니다.

## CAD 교육자료 생성기 (MIDAS 와 별개)

AutoCAD 기본 명령어 교육용 DXF(R2018, mm, 모델공간 1:1)를 만듭니다. MIDAS·네트워크 연동은 없습니다.

```
pip install -r requirements.txt
python -m tools.cad_training --out output/cad_training            # DXF 6개 + 시트별 PNG
python -m tools.cad_training --out output/cad_training --no-preview
```

산출 파일 (`output/cad_training/`, git 추적 안 함):

| 파일 | 내용 |
|---|---|
| `M1_그리기.dxf` / `M1_그리기_정답.dxf` | 예제 6매(LINE·CIRCLE·ARC·RECTANG·PLINE·POLYGON) + 실습 3매 / 정답 3매 |
| `M2_수정.dxf` / `M2_수정_정답.dxf` | 예제 10매(MOVE~ARRAY) + 실습 3매 / 정답 3매 |
| `C1_종합실습.dxf` / `C1_종합실습_정답.dxf` | 종합 실습 1매 / 정답 1매 |
| `preview/<시트ID>.png` | 시트마다 미리보기 1장 (예: `M1-E01.png`) |

- 시트는 A3 도곽(420×297)으로, 모델공간 X 방향으로 470 간격으로 나열됩니다.
- 시트ID: `M1-E01`(예제) / `M1-P01`(실습) / `M1-A01`(정답, 같은 번호 실습과 1:1).
- 문자 스타일 `KOR` 은 맑은고딕(`malgun.ttf`)을 씁니다. 맑은고딕이 없는 PC(macOS·Linux 등)에서는 CAD 프로그램이 대체 글꼴로 표시하므로 한글이 깨지거나 폭이 달라 보일 수 있습니다.
- 테스트: `python -m pytest tests/cad_training`
