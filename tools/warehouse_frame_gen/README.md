# warehouse_frame_gen — 창고 기본 프레임 생성기

원본 `창고설계용 기본 프레임 생성.py` (532줄, Tkinter GUI)의 검증된 순수
지오메트리 함수 5개를 **바이트 단위 그대로 이식**하고, GUI/네트워크 결합
코드만 재구성한 도구.

```
python -m tools.warehouse_frame_gen --make-template form.xlsx   # 빈 폼 생성
python -m tools.warehouse_frame_gen --template form.xlsx --dry-run
python -m tools.warehouse_frame_gen --template form.xlsx --mapi-key <KEY>
```

종료코드: `0` 정상 / `2` 인자·환경·span 식 파싱 오류 / `3` 쓰기 실패(id 범위 보고) /
`4` 비어있지 않은 모델 / `5` matl·sect id 없음.

## 이식한 원본 함수 (`geometry.py`, 변경 없음)

`spans_to_coords` · `parse_span_expression` · `make_grid_nodes_indexed` ·
`make_grid_elements` · `add_ridge_roof`.

`build_model()` 은 원본 `build_and_send()` 의 결합부(순서·인자 전달)를 그대로
옮기되 네트워크/GUI/로그만 제거한 것이다. `write_model()` 이 PUT 만 담당한다.

## 원본에서 확인된 실제 동작 (코드에서 읽어 옮김)

아래는 "어떻게 동작해야 하는가"가 아니라 **이식된 원본 코드가 실제로 하는 것**이다.

- **`skip_bottom_beam` 은 X·Y 양방향**. `is_skipped_x(k)` 와 `is_skipped_y(k)` 둘 다
  `k == 0` 에서 True → 최하부 층(k=0)의 X방향 보와 Y방향 보를 **모두** 생략한다.
- **`skip_top_beam` 은 Y방향만**. `is_skipped_y(k)` 만 `k == top_k` 에서 True →
  지붕층의 Y방향 보만 생략. 지붕층 X방향 보는 `skip_top_x_beam` 이 따로 제어한다.
- **`skip_top_x_beam` = `use_ridge`**. `build_model` 이 `make_grid_elements(...,
  skip_top_x_beam=use_ridge)` 로 넘긴다. 용마루를 쓰면 `make_grid_elements` 는
  지붕층 X방향 보를 **만들지 않고**, `add_ridge_roof` 가 세분화해서 다시 만든다.
- **용마루 지붕 X보 "재구성" 은 replace 가 아니라 skip + add**. `add_ridge_roof` 는
  `elem_assign` 에 **덧붙이기만** 한다(in-place). 기존 지붕 X보를 지우는 코드는
  없다 — 애초에 `make_grid_elements` 에서 건너뛰었기 때문에 중복이 안 생긴다.
- **용마루 축은 X평행, Y중앙 고정**. 용마루 절점은 `y_mid = (y_vals[0] +
  y_vals[-1]) / 2`, 높이 `top_z + rise` 에 놓이며 X방향으로만 이어진다. `ny==1`
  이면 `y_mid == y_vals[0]`.
- **중도리(purlin)는 절점 + 요소 둘 다**. `add_ridge_roof` 5)에서 중도리 절점을,
  6)에서 서까래 BEAM 요소(처마→중도리들→용마루 체인)를, 7)에서 중도리 X방향
  BEAM 요소를 만든다.
- **`connect_rafters=False`** 면 3)처마 X보 + 4)용마루 X보까지만 만들고 즉시
  반환한다. 서까래·중도리·중도리보는 없다.
- **기둥은 skip 옵션과 무관하게 항상 생성**. `make_grid_elements` 의 Z방향
  루프에는 skip 검사가 없다.
- **ID 연속성**. `add_ridge_roof` 는 `node_start_id` / `elem_start_id`(=기본
  그리드 다음 번호)부터 순차 증가시킨다. 하드코딩 오프셋 없음. 기둥 위치의
  처마 절점은 기존 그리드 절점을 재사용하고, 베이 중간 위치만 신규 생성한다.

## 표시용 카운트 분해

`geometry._derive_counts()` 는 콘솔 요약(X보/Y보/기둥/처마X보/용마루X보/서까래/
중도리보)을 위한 산술 유도값이다. **authoritative 는 `build_model` 이 반환하는
`node_assign`/`elem_assign` 딕셔너리 길이**이며, 분해 합이 그와 일치하는지는
테스트(`test_geometry.py`)가 옵션 매트릭스 전체에서 검증한다.

## 라이브 쓰기 미검증 경계

**이 도구의 PUT 왕복(`db/UNIT` / `db/NODE` / `db/ELEM`)은 실제 MIDAS 로 검증되지
않았다.** 빈 MIDAS 모델을 확보하지 못했고, `midas-api` catalog 스키마에
기반한 구현이다. `db/SWIND`(catalog `active_methods=[]` 이나 라이브 GET 200) ·
portal_frame_gen PR #9(가드 우회) 전례처럼 **catalog ↔ 라이브 불일치가
가능**하다.

- 첫 쓰기 = `PUT db/UNIT`. 405/401/403/"not supported" → 즉시 중단(exit 2).
- 쓰기 전 전제조건(빈 모델 가드, matl/sect 존재 확인)은 모두 GET 이며 **어떤
  PUT 보다 먼저** 실행된다. `PUT db/UNIT` 이 모델 단위를 덮어쓰지만, 그 앞에서
  가드가 빈 모델임을 확인했으므로 허용된다(portal PR #9 QA 반려 반영).
- 모든 PUT 응답을 성공(무바디 / 에코된 컬렉션 키 / `Assign` 에코)과 에러
  (`{"error":...}` / 컬렉션 키 없는 `{"message":...}`) 두 형태로 방어적으로
  파싱한다. 첫 실패에서 중단하고 그때까지 쓴 id 범위를 보고한다(exit 3).

프로덕션 투입 전, 빈 모델 + `matl`/`sect` id 가 정의된 상태에서 실제 생성 후
MIDAS 에서 결과를 육안 확인할 것.

## 스코프 밖

하중·하중조합·자중, 해석 실행, 결과 추출, 재료·단면 생성, BEAM 외 요소타입,
`db/CONS` 지점(원본이 만들지 않음), 라이브 쓰기 검증, `midas_common` 공용 추출,
원본 지오메트리 로직 변경.
