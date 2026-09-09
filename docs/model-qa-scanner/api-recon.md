# MIDAS Gen NX 모델 QA 스캐너 — API 정찰 (참고자료)

> `midas-api` 스킬 `endpoint_catalog.json`(669 항목) 기준 정찰 결과. 태스크 1 산출물.
> catalog 항목 형식: `input_uri`(= `db/<NAME>`) / `active_methods` / `schema` / `example` / `specs`(필드표).

## 공통

- **응답 봉투**: `{ "<KEY>": { "<id>": { …필드… }, … } }` (예: `{"NODE":{"1":{"X":..,"Y":..,"Z":..}}}`).
  GET-all(id 없이 컬렉션 전체) = `GET {base}/db/<NAME>`. 페이지네이션/크기제한 파라미터는 스키마에 없음.
- **단위**: `db/UNIT` (`GET`, `PUT` 만) → `{"UNIT":{"1":{"FORCE","DIST","HEAT","TEMPER"}}}`.
  FORCE∈{N,KN,KGF,TONF,KIPS…}, DIST∈{M,CM,MM,FT,IN}.
- **미지원 처리**: catalog 에 `input_uri` 없음 → API 접근 불가. `active_methods` 가 `[]` → 리소스는 존재하나 어떤 verb 도 없음(읽기 불가). HTTP 에러코드는 catalog 미기재 → 라이브 확인 필요.

## A. 모델 점검용 리소스 (실제 경로 확정)

| 논리명 | 실제 경로 | verbs | 핵심 필드 |
|---|---|---|---|
| 절점 | `db/NODE` | POST/GET/PUT/DELETE | `X,Y,Z` (id=절점번호 키) |
| 요소 | `db/ELEM` | 〃 | `TYPE`(BEAM/TRUSS/PLATE/TENSTR/WALL…), `MATL`(int), `SECT`(int, 단면/두께 공용), `NODE`(int[]), `ANGLE`, `STYPE`, `WALL` |
| 재료 | `db/MATL` | 〃 | `TYPE`, `NAME`, `DAMP_RAT`, `PARAM`[{`ELAST`(E), `POISN`, `DEN`(중량밀도), `MASS`(질량밀도), `THERMAL`}] |
| 단면 | `db/SECT` | 〃 (변형 17종) | `SECTTYPE`, `SECT_NAME`, `SECT_BEFORE`{...} |
| 두께 | `db/THIK` | (스키마상 존재) | 판/슬래브 두께 |
| 지점 구속 | `db/CONS` (Constraint Support) | 〃 | `ITEMS`[{`ID`,`GROUP_NAME`,`CONSTRAINT`}]. `CONSTRAINT`="1111000"=[DX,DY,DZ,RX,RY,RZ,RW] |
| 점 스프링 | `db/NSPR` (Point Spring) | 〃 | `ITEMS`[{`TYPE`,`SDR`[6],`F_S`[6],`GROUP_NAME`}] |
| 일반 스프링 | `db/GSTP`(타입) + `db/GSPR`(배정) | 〃 | |
| 면 스프링 | `db/SSPS` (Surface Spring) | 〃 | |
| 강제변위 지점 | `db/SDSP` | 〃 | |
| 강체 링크 | `db/RIGD` (Rigid Link) | 〃 | `ITEMS`[{`ID`,`GROUP_NAME`,`DOF`(6자리 비트),`S_NODE`(int[] 종속절점)}]. 마스터=Assign 키 |
| 탄성 링크 | `db/ELNK` (Elastic Link) | 〃 | `NODE`[2], `LINK`(GEN/RIGID/TENS/COMP…), `SDR`[6], `BNGR_NAME` |
| 층 정의 | `db/STOR` (Story Data) | 〃 | `STORY_NAME`, `STORY_LEVEL`, `bFLOOR_DIAPHRAGM`(bool), `WIND_FLOOR_WIDTH_X/Y`, `WIND_CENTER_X/Y`, `WIND_ECCENT_X/Y`, `SEIS_ACC_ECCENT_X/Y`, `SEIS_INHERENT_ECCENT_X/Y`, `SEIS_TORSIONAL_AMP_FACTOR_X/Y` |
| 다이어프램 해제 | `db/DRLS` (Diaphragm Disconnect) | 〃 | 강막 제외 절점 목록 |
| 정적 하중케이스 | `db/STLD` (Static Load Cases) | 〃 | `NO`(RO), `NAME`, `TYPE`(D/L/W/E/…), `DESC` |
| 절점하중 | `db/CNLD` (Nodal Loads) | 〃 | `ITEMS`[{`ID`,`LCNAME`,`FX,FY,FZ,MX,MY,MZ`}] |
| 보하중 | `db/BMLD` (Beam Loads) | 〃 | `ITEMS`[{`LCNAME`,`CMD`,`TYPE`,`DIRECTION`,`D`[4],`P`[4]}] |
| 압력하중 | `db/PRES` (Pressure Loads) | 〃 | `ITEMS`[{`LCNAME`,`ELEM_TYPE`,`FACE_EDGE_TYPE`,`DIRECTION`,`FORCES`[5]}] |
| 자중 | `db/BODF` (Self-Weight) | 〃 | `LCNAME`, `FV`[3]=[X,Y,Z] |
| 하중조합 | `db/LCOM-GEN` / `LCOM-CONC` / `LCOM-STEEL` / `LCOM-SRC` / `LCOM-STLCOMP` / `LCOM-SEISMIC` | 〃 | 설계타입별 개별 엔드포인트. 참조 케이스·계수 |
| 구조 그룹 | `db/GRUP` (Structure Group) | POST/GET/PUT | `NAME`, `N_LIST`(int[]), `E_LIST`(int[]) |
| 경계 그룹 | `db/BNGR` (Boundary Group) | POST/GET/PUT | |
| 하중 그룹 | `db/LDGR` (Load Group) | 〃 | |
| 절점 질량 | `db/NMAS` (Nodal Masses) | POST/GET/PUT/DELETE | |
| 하중→질량 | `db/LTOM` (Loads to Masses) | 〃 | |

**없는 것**: `db/BNDR`, `db/SPRT`, `db/STRY`, `db/DIAP`, `db/STLDCASE`, `db/LCOM`(무접미사), `db/NDMS`, `db/SMASS`, `db/LMASS`, `db/WIND`, `db/SEIS`, `db/RSFN`, `db/RSCS`.

## B. 풍/지진 적용조건 — 핵심 확답

| 항목 | 경로 | verbs | GET 조회 | 노출 파라미터 |
|---|---|---|---|---|
| **자동 풍하중 정의** | `db/SWIND` (Static Wind Load — KDS 41-12:2022 / User Type) | catalog 상 `[]` / **라이브 GET 200 동작 확인 (2026-09-09)** | **가능(라이브)** | catalog 의 `active_methods=[]` 는 부정확 — 실제 `GET db/SWIND` 는 HTTP 200 + 전체 데이터 반환. 필드: `PARAMETERS.WIND_SPEED`(Vo), `PARAMETERS.EXP_CATEGORY`(0~3 = A~D 지표면조도), `PARAMETERS.IMPORTANCE_FACTOR`(Iw), `PARAMETERS.GUST_FACTOR_X/Y`(Gf), `PARAMETERS.ROOF_HEIGHT`(기준높이), `PARAMETERS.TOPOGRAPHIC_EFFECT.OPT_USE`(지형계수), `PARAMETERS.FORCE_COEF.OPT_USE`, `WIND_CODE`(기준코드), `SCALE_FACTOR_X/Y`, `PROFILE.X_DIR[]/Y_DIR[].PRESSURE`(설계속도압). → 스캐너는 `db/SWIND` 직접 파싱, 값출처=`API조회`. (에러/빈 응답 시에만 `db/STLD`+`db/STOR` 간접 폴백.) |
| **자동 지진하중(정적)** | `db/SSEIS` (KDS 41-17-00:2019 / User) + `db/POSL` (Parameter of Seismic Loads) | POST/GET/PUT/DELETE | **가능** | `db/SSEIS`: `SEIS_ZONE`(지역), `EPA`(유효지반가속도), `SITE_CLASS`(S1~S6), `FA`/`FV`, `SDS`/`SD1`, `SEIS_USE_GROUP`, `IMPORTANCE_FACTOR`(Ie), `PERIOD_METHOD`(해석/근사), `PERIOD_ANALYSIS_X/Y`, `PERIOD_APPR_X/Y`, `SCALE_FACTOR_X/Y`, `ACCIDENT_ECCEN_X/Y`, `ACCIDENT_TORSION`. `db/POSL`: `RMF`(반응수정계수 R), `METHOD`(RES_DISP/EQV_STATIC). **감쇠비 없음.** |
| **응답스펙트럼 함수** | `db/SPFC` (Response Spectrum Functions — Korea/US/EU/China/Japan/Taiwan/India/Other 8종) | POST/GET/PUT/DELETE | 가능 | 국가별 서브스키마. `db/RSFN`·`db/SPFN` 없음 — 실제 이름은 `db/SPFC`. |
| **RS 하중케이스** | `db/SPLC` (Response Spectrum Load Cases) | POST/GET/PUT/DELETE | 가능 | `NAME`, `DIR`(XY/Z), `ANGLE`, `SCALE`, `PMFT`, `aFUNCNAME`(함수명), `COMTYPE`(SRSS/CQC/ABS), `bDAMP`/`DALL`(전 모드 감쇠비)/`aDAMPING`(모드별), `bACCECC`/`ACCECC_PERTCENT`(우발편심 %), `iSIGNTYPE`. `db/RSCS`·`db/RSPL` 없음. |

## C. 부가

- **모델 단위 판별**: `db/UNIT` GET → `FORCE`/`DIST`/`HEAT`/`TEMPER`.
- **시공단계**: `db/STAG` (Define Construction Stage) 존재, GET 지원. `NAME`, `DURATION`, `ACT_ELEM`/`DACT_ELEM`(활성/비활성 구조그룹+`AGE`), `ACT_BNGR`/`DACT_BNGR`, `ACT_LOAD`/`DACT_LOAD`. 부가: `db/STCT`, `db/CSCS`, `db/TMLD`. → 시공단계 모델 "미지원" 아님. 비활성 요소 = `db/STAG` (D)ACT_ELEM ↔ `db/GRUP`.
- **Story 결과표**(`POST/TABLE`, 모델 데이터 아님, 스캐너 스코프 밖): Story Drift / Story Shear / Torsional Irregularity / Soft Story / Weak Story / Story Eccentricity 등.
