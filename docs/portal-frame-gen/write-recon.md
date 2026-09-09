# MIDAS Gen NX 쓰기 경로 정찰 — 포탈 프레임 생성기 (태스크 1)

> `midas-api` 스킬 `endpoint_catalog.json`(669 항목, `input_uri` 키) 의 `active_methods` / `schema` /
> `example` / `specs` 기준. 스캐너용 `docs/model-qa-scanner/api-recon.md`(읽기 정찰) 와 별도 파일.
>
> **스코프 (Main 확정, Plan 정정 반영)**: 재료·단면은 **사전 정의 요구** — 생성기는 만들지 않고
> 기존 id 를 **배정만** 한다. 따라서 `PUT db/MATL` / `PUT db/SECT` 는 정찰 대상 아님.
> 대신 `GET db/MATL` / `GET db/SECT` 로 **이름 → id 매핑**하는 방법이 핵심(§3).
> **(b) 라이브 쓰기 왕복은 미실시** — 빈 모델 없음(§8).

## 0. 공통 — 쓰기 요청 봉투

- **엔드포인트**: `PUT {base}/db/<NAME>` (base = `https://moa-engineers.midasit.com:443/gen`, 헤더 `MAPI-Key`).
- **바디**: `{"Assign": {"<ID>": { …필드… }, …}}`
  - 최상위 래퍼는 `Assign` (GET 응답의 `{"<KEY>": {"<id>": …}}` 봉투와 다름).
  - `<ID>` 는 catalog `example` 전부 **문자열 키로 직접 지정**
    (`"Assign": {"1": {...}}`, `"Assign": {"198": {...}}`). 자동 채번 여부는 라이브 미검증(§8).
  - `"//"` 필드는 catalog 예시의 주석 — 실제 요청엔 불필요.
- **한 요청에 복수 ID** 가능: `{"Assign": {"1": {...}, "2": {...}}}`.
- **응답 / 에러 형식**: catalog 미기재 — 라이브 미검증(§8).

## 1. `db/NODE` — 절점 (생성)

| 항목 | 값 |
|---|---|
| verbs | `POST` / `GET` / `PUT` / `DELETE` |
| 바디 | `{"Assign": {"1": {"X": -1, "Y": -1, "Z": -1}, "2": {"X": -2, "Y": -2, "Z": -2}}}` |
| 필드 | `X` `Y` `Z` (Number, 각 default 0, 전부 Optional). 전역좌표, 단위 = 현재 모델 `db/UNIT.DIST`. |
| ID | Assign 키 = 절점번호 |

## 2. `db/ELEM` — 요소 (생성, 기존 MATL/SECT id 참조)

| 항목 | 값 |
|---|---|
| verbs | `POST` / `GET` / `PUT` / `DELETE` |
| 바디(보) | `{"Assign": {"198": {"TYPE": "BEAM", "MATL": 1, "SECT": 1, "NODE": [30, 74], "ANGLE": 0}}}` |
| `TYPE` | String, default `"BEAM"`. 포탈 프레임 기둥·보 = `"BEAM"`. (예시 기타값: `TRUSS`, `TENSTR`) |
| `MATL` | Integer, **Required** — **기존 `db/MATL` id** (§3 에서 이름으로 조회). |
| `SECT` | Integer, **Required** — **기존 `db/SECT` id** (§3). 판요소면 `db/THIK` id. |
| `NODE` | Array[Integer], **Required**. 보/트러스 `[i, j]`. 최대 8. |
| `ANGLE` | Number, default 0. 베타각. |
| ID | Assign 키 = 요소번호 |

## 3. DB 재료 / 단면 — **이름 → id 조회 방법** (생성기 매핑용)

생성기는 템플릿의 재료명·단면명을 받아 **현재 모델에 이미 정의된** `db/MATL` / `db/SECT` 에서
일치하는 id 를 찾아 `db/ELEM.MATL` / `.SECT` 에 넣는다. 이름이 없으면 **중단**(사전 정의 요구).

### 3a. `GET db/MATL` — 재료명 → id

- **요청**: `GET {base}/db/MATL` (id 없이 전체).
- **응답 봉투**: `{"MATL": {"<id>": { …필드… }, …}}` — 최상위 키 `MATL`, 그 아래 **문자열 id → 재료 객체**.
- **매칭할 이름 필드**:
  | 필드 | 위치 | 내용 | 매칭 용도 |
  |---|---|---|---|
  | `NAME` | 재료객체 최상위 | 재료 표시명 (예: `"SS275"`, `"DB_Steel"`) | **1순위 매칭 키** — 템플릿이 지정하는 이름 |
  | `TYPE` | 재료객체 최상위 | `"STEEL"` / `"CONC"` / `"SRC"` / `"ALUMINUM"` / `"User"` | 종류 교차확인 |
  | `PARAM[0].DB` | `PARAM` 배열 0번 | DB 강종명 (예: `"S450"`, `"SS275"`) | `NAME` 이 관용명일 때 보조 매칭 |
  | `PARAM[0].STANDARD` | `PARAM` 배열 0번 | DB 표준코드 (예: `"KS21(S)"`, `"EN05(S)"`) | 표준 교차확인 |
- **조회 로직 권장**: `NAME == 템플릿명` 우선, 실패 시 `PARAM[0].DB == 템플릿명`. 복수 매칭이면 최소 id.
- **빈 컬렉션**: 재료 0개면 `{"message": ""}` 반환(HTTP 200) — 스캐너에서 확인된 관례. 이 경우 "사전 정의 없음" 으로 중단.

### 3b. `GET db/SECT` — 단면명 → id

- **요청**: `GET {base}/db/SECT`.
- **응답 봉투**: `{"SECT": {"<id>": { …필드… }, …}}` — 최상위 키 `SECT`, **문자열 id → 단면 객체**.
- **매칭할 이름 필드**:
  | 필드 | 위치 | 내용 | 매칭 용도 |
  |---|---|---|---|
  | `SECT_NAME` | 단면객체 최상위 | 단면 표시명 (예: `"H400x200x8x13"`, `"H-Section_DB"`) | **1순위 매칭 키** |
  | `SECTTYPE` | 단면객체 최상위 | `"DBUSER"` / `"VALUE"` / `"TAPERED"` / `"SRC"` / `"PSC"` … | 종류 교차확인 |
  | `SECT_BEFORE.SHAPE` | 중첩 | 형상코드 `"H"` `"L"` `"C"` `"B"` `"P"` … | H형강 여부 확인 |
  | `SECT_BEFORE.SECT_I.SECT_NAME` | 중첩 | DB 호칭 (예: `"H100x100x6/8"`) | `SECT_NAME` 이 별칭일 때 보조 매칭 |
  | `SECT_BEFORE.SECT_I.DB_NAME` | 중첩 | DB 카탈로그명 (예: `"KS21"`) | 표준 교차확인 |
- **주의**: catalog 상 `db/SECT` 는 17개 변형(`Common`/`DB/User`/`Value`/`Tapered-*`/`Composite-*`/`PSC*`/`SRC`/`Steel Girder`)이 **같은 `input_uri`** 에 등재. `GET db/SECT` 는 전 변형을 한 봉투로 돌려줄 것으로 추정(라이브 확인). 변형 구분은 `SECTTYPE` 로.
- **빈 컬렉션**: `{"message": ""}` → 중단.

### 3c. 요소가 참조하는 필드 (배정만)

- `db/ELEM.MATL` = 위 3a 에서 찾은 id (Integer).
- `db/ELEM.SECT` = 위 3b 에서 찾은 id (Integer).
- 잘못된 id(없는 재료/단면) 참조 시 응답 형태는 라이브 미검증(§8).

## 4. `db/CONS` — 절점 구속 (지점, 생성)

| 항목 | 값 |
|---|---|
| verbs | `POST` / `GET` / `PUT` / `DELETE` |
| 바디 | `{"Assign": {"1": {"ITEMS": [{"ID": 1, "GROUP_NAME": "Service", "CONSTRAINT": "1111000"}]}}}` |
| Assign 키 | 절점번호 (예시에서 키 `"1"` = `ITEMS[].ID` 1) |
| `ITEMS[].ID` | Integer — 구속 대상 절점번호 |
| `ITEMS[].GROUP_NAME` | String — 경계그룹명. 미지정 시 `""` 허용 여부 라이브 확인(§8) |
| `ITEMS[].CONSTRAINT` | String — 자유도 비트, **순서 `(DX, DY, DZ, RX, RY, RZ, RW)` = 7자리**. `1`=구속/`0`=자유. 고정 `"1111110"`, 핀 `"1110000"`. |

## 5. `db/UNIT` — 단위계 (생성, 가장 먼저)

| verbs | `GET` / `PUT` (**POST/DELETE 없음**) |
|---|---|
| 바디 | `{"Assign": {"1": {"FORCE": "KN", "DIST": "M", "HEAT": "KCAL", "TEMPER": "C"}}}` |
| 필드 | `FORCE`(N/KN/KGF/TONF/KIPS/LBF…), `DIST`(M/CM/MM/FT/IN), `HEAT`, `TEMPER` |
| 주의 | Assign 키 `"1"` 고정(단일 레코드). **NODE/SECT 치수 해석 기준이므로 최우선 PUT.** |

## 6. `db/GRUP` — 구조그룹 (선택)

| verbs | `POST` / `GET` / `PUT` (**DELETE 없음**) |
|---|---|
| 바디 | `{"Assign": {"1": {"NAME": "Columns_", "P_TYPE": 0, "N_LIST": [1, 2], "E_LIST": [1, 2]}}}` |
| 필드 | `NAME`(String), `P_TYPE`(Integer, 보통 0), `N_LIST`(Array[Integer]), `E_LIST`(Array[Integer]) |

## 7. 생성 순서 (권장, 태스크 2)

1. `PUT db/UNIT` — kN, m
2. `GET db/MATL` → 템플릿 재료명으로 **기존 id 확보** (없으면 중단)
3. `GET db/SECT` → 템플릿 기둥/보 단면명으로 **기존 id 확보** (없으면 중단)
4. `PUT db/NODE` — 기둥 하단 2점 + 처마 2점 (+ 게이블이면 용마루 1점)
5. `PUT db/ELEM` — 기둥 2 + 보 2 (`TYPE:"BEAM"`, `MATL`/`SECT` = 2·3 에서 얻은 id, `NODE:[i,j]`)
6. `PUT db/CONS` — 기둥 하단 2절점 (핀 `"1110000"` 또는 고정 `"1111110"`)
7. (선택) `PUT db/GRUP` — `Columns_` / `Rafters_`
8. 각 단계 `GET` 왕복 검증

## 8. 라이브 쓰기 미검증 경계 (Main 지시: 라이브 정찰/빈 모델 준비 안 함)

> **이 생성기는 catalog 스키마 기반 구현이며, 실제 MIDAS 쓰기 왕복은 미검증이다.**
> **QA 단계 또는 사용자가 빈 모델로 실행할 때 확인이 필요하다.**
> **`db/SWIND` 전례처럼 catalog ↔ 라이브 불일치 가능성이 있다** (SWIND 는 catalog 상
> `active_methods=[]` 이었으나 라이브 GET 200 동작). 아래 항목은 코드가 방어적으로 처리하되
> 실제 동작은 라이브에서만 확정된다.

1. **첫 쓰기 = `PUT db/UNIT`** — 임시 노드 프로브(id 9001 PUT→GET→DELETE) **안 함**.
   `PUT db/UNIT` 응답이 405/401/403 또는 "not supported" 면 **즉시 중단**
   (exit 2, "라이브 쓰기 미지원 가능성 — Main 보고 필요"), 이후 쓰기 없음.
2. **응답 파싱은 성공·에러 두 형태 모두 방어적으로**:
   - 성공: `{"NODE": {...}}` 류 봉투 또는 200 무바디.
   - 에러: `{"error": {"code", "message"}}` 또는 `{"message": "..."}`.
   - 첫 실패에서 중단, 성공한 step·id 범위 보고 (exit 3).
3. **ID 지정 존중** — `Assign` 키로 준 ID 가 그대로 들어가는지(자동 재채번 아님). 라이브 미검증.
4. **POST vs PUT 의미** — 관례상 `PUT`=지정 ID upsert, `POST`=일괄 생성. catalog 에 구분 텍스트 없음.
5. **DELETE 형식** — `active_methods` 에 `DELETE` 있음(NODE/ELEM/CONS/MATL/SECT; UNIT·GRUP 은 없음).
   경로형 `DELETE {base}/db/NODE/1` vs 바디형 vs ID 리스트 — 미기재. `--rollback` 은 조건부(지원 시만).
6. **에러 응답 실제 형태** — 없는 `MATL`/`SECT` id 참조 PUT 시 응답. 라이브 미검증.
7. **`GET db/SECT` 17변형 통합 여부** — 한 봉투로 오는지, id 네임스페이스 공유 여부. 라이브 미검증.
8. **`db/CONS.GROUP_NAME`** — 미지정(`""`) 허용 여부. 안 되면 `"Service"` 등 기본값으로 폴백.

## 9. 빈 모델 가드 (필수, 생략 불가)

`GET db/NODE` + `GET db/ELEM` → 노드/요소가 하나라도 있으면 **반드시 중단**(exit 4).
`--force` 만 우회하며, 우회 시 요란한 경고 출력. `db/MATL`/`db/SECT`/`db/CONS` 가 비어있지 않은 것은
정상(재료·단면 사전 정의 요구) — 경고만.

## 스코프 밖

`PUT db/MATL` / `PUT db/SECT` (재료·단면 생성) — 스코프 제외, 사전 정의 요구.
하중·조합·층·메시·헌치·퍼린·가새·다층·imperial·해석 실행 — 태스크 2 스코프 밖.
