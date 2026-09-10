# 승인 기록 — 2026-09-10

> **성격**: 무엇이 **누구에 의해 어떤 근거로** 정해졌는지 그대로 적는다. 위조 0 · PROPOSED ≠ APPROVED.
> **★ 서명 결재문이 아니다.** 구두 승인을 서명 결재로 위장하지 않는다.
> 대상: `CEO_APPROVAL_REQUEST_20260910.md` v4 (결재 1~6)
> **개정 이력**: 초판(택일 4건 PENDING) → 2026-09-10 개정 — 구두 포괄 승인·실행 위임 반영, V-11 조건 4·5 모바일 실측 종결.

---

## 0. Provenance — 누가 무엇을 했나

```
Grant (대표)
  → 결재안 전반에 대한 진행 구두 승인 ("그냥 하라", 2026-09-10)
  → 구체 실행 선택은 실무에 위임

Brian (CTO)
  → 위임 범위 내에서 실행안 선택

Counsel (자문 변호사)
  → 법률 판단 항목은 여전히 미확정
```

★ **대표가 각 선택지(H13 (4) · T-6/T-7 삭제 · GPS (a) · 제7조 (a))를 직접 고른 것이 아니다.**
포괄 승인과 실행 위임이 있었고, 선택은 Brian 이 했다. 이 문서는 그 구분을 유지한다.

### 상태 어휘 (신규 정의)

| 상태 | 뜻 |
|---|---|
| `APPROVED_VERBAL` | 대표가 그 항목 자체를 구두 승인. 예/아니오 항목 |
| `APPROVED_VERBAL_DELEGATED_EXECUTION` | 대표는 진행을 승인하고 선택은 위임 |
| `EXECUTION_DECIDED_BY_BRIAN_UNDER_VERBAL_DELEGATION` | 위임 범위 내 Brian 의 실행 선택 |
| `APPROVED_CONDITIONAL_FACT_VERIFICATION` | 정책은 정해졌으나 사실 확인 전까지 확정 아님 |
| `COUNSEL_PENDING` | 법률 판단 미확정. 사내 결정으로 대체하지 않는다 |

**서명본 없음.** 서명이 오면 각 항목에 일자·서명을 기입하고 상태를 승격한다.

---

## 1. 항목별

| # | 항목 | 상태 | 선택 | 비고 |
|---|---|---|---|---|
| **1** | H13 — 개시 법역 | `EXECUTION_DECIDED_BY_BRIAN_UNDER_VERBAL_DELEGATION` | **(4)** OTHER 기본 차단 + 국가별 launch allowlist | 구현 완료 · 신규 테스트 통과. ★ **기존 테스트 5건과 충돌 — 적용 범위 미확정, §5** |
| **2** | D-16 — KR·CN 부속조항 미작성 구조 | `APPROVED_VERBAL` | 승인 | KR 법정 고지사항 충족 여부는 **`COUNSEL_PENDING` 유지** |
| **3** | T-6 / T-7 — 방침 제11조 | `EXECUTION_DECIDED_BY_BRIAN_UNDER_VERBAL_DELEGATION` | `:191` **삭제** · `:194` **삭제** | 공개 방침에 미구현 로드맵을 적지 않는다 |
| **4** | V-11 — 농장 GPS | `EXECUTION_POLICY_DECIDED_BY_BRIAN_UNDER_VERBAL_DELEGATION`<br>→ 최종 `APPROVED_CONDITIONAL_FACT_VERIFICATION` | **(a)** 사용하지 않는다 | ★ 사실 확인 6조건 중 2건 미완 — §3 |
| **5** | `pigos_ro` | `APPROVED_VERBAL` | 승인 (범위 6항) | ★ 생성 못 함 — §4 |
| **6** | 제7조 `[COUNSEL]` | `EXECUTION_DECIDED_BY_BRIAN_UNDER_VERBAL_DELEGATION` | **(a)** 공개 조항으로 전환 | D-13 은 `COUNSEL_PENDING` 유지 |

---

## 2. 실행 결과

### 닫힌 것

```
D-16    terms_renderer._GROUP_ADDENDUM 에 "KR": None, "CN": None, "OTHER": None 명시 + 사유 주석
        jurisdiction._ADDENDUM 과 전 그룹 동일 응답 확인 (테스트)
        fallback semantics 변화 0 · 타 법역 문서 세트 변화 0

H13     jurisdiction._LAUNCH_ALLOWLIST = {"US"} 신설 (국가 단위)
        기존 _GATES / signup_blocked 재사용 — 중복 게이트 없음
        기존 차단 사유(KR_REFERENCE_ONLY · HOLD_D07) 를 덮어쓰지 않음
        ★ 부수 효과: BR·DE·GB·TH·VN 가입도 닫힌다 (R-10 포함) — 범위 미확정, §5 참조

T-6/T-7 방침 제11조 :191 "취약점 점검" 삭제 · :194 재식별 방지 항 삭제
        제11조 서두 담요 단서("[운영 실측 필요 — V프로세스]") 삭제

제7조   "[COUNSEL]" → "본 조의 역할 구분은 법률 검토 중이며, 확정 시 제15조에 따라
        개정·고지합니다" 공개 조항으로 전환 (ko·en)

마커    공개 서빙본 언어별 24 → 1

V-11    조건 4·5 (모바일) 종결 — §3
```

### 남은 것

```
V-11    정밀 위치정보 1건 — 조건 1·6 (프로덕션 DB) 미완. ★ A 정정 배포의 유일한 blocker
```

---

## 3. V-11 — 확정 조건 6개 중 4개 종결, 2개 미확인 (둘 다 DB)

| # | 조건 | 결과 | 근거 |
|---|---|---|---|
| 1 | prod `farms.gps_lat/gps_lng` non-null = 0 | **미확인** | 프로덕션 조회 경로 없음 (§4) |
| 2 | API write path 없음 | **없음** | `api/app` 전체에서 `gps` 참조 0건 (모델 정의 제외) |
| 3 | Web write path 없음 | **없음** | `src/` 에 `gps_lat`·`geolocation`·`getCurrentPosition` 0건 |
| 4 | Android / iOS location permission·precise path | **없음** (2026-09-10 실측) | 아래 §3-1 |
| 5 | analytics/SDK precise location 수집 없음 | **없음** (2026-09-10 실측) | 아래 §3-1 |
| 6 | backup·log·EXIF 보유 정황 | **부분** — EXIF 유입 경로 없음 확인 · backup/log 는 미확인 | §3-1 · 나머지는 1과 동일 제약 |

**모델·마이그레이션 실측**: `platform.py:77-78` 에 nullable 컬럼 정의. DDL 4곳(`FLOAT` 선언).
**INSERT·VALUES 로 값을 넣는 코드는 저장소 전체에서 0건.**

### 3-1. 모바일 실측 (2026-09-10, machine `bjh`)

저장소가 이 워크스테이션에 있어 조건 4·5 를 직접 측정했다.

```
대상       C:\dev\pigos-android  (HEAD 183aaa8)   소스 343개 파일
           C:\dev\pigos-ios      (HEAD 0b560aa)   소스 171개 파일

권한       AndroidManifest.xml 2개(main·debug) 의 uses-permission 전량:
             INTERNET · ACCESS_NETWORK_STATE · RECEIVE_BOOT_COMPLETED
             POST_NOTIFICATIONS · CAMERA
           → ACCESS_FINE_LOCATION · ACCESS_COARSE_LOCATION
             ACCESS_BACKGROUND_LOCATION  0건

           Info.plist 2개(App·Widget) 의 UsageDescription 전량:
             NSCamera · NSFaceID · NSMicrophone · NSSpeechRecognition
           → NSLocation*UsageDescription  0건

코드       FusedLocationProvider · LocationManager · CLLocationManager
           getCurrentPosition · requestLocationUpdates · Geolocator
           startUpdatingLocation · gps_lat · gps_lng · gpsLat · gpsLng
           → 양 저장소 합계 0건 (build·Pods·.git 제외)

SDK        Android  firebase-bom 33.7.0 + firebase-messaging (FCM 푸시) 만.
                    firebase-analytics · play-services-location ·
                    타사 analytics/광고 SDK 0건.
                    google-services 플러그인은 app/google-services.json 이
                    있을 때만 적용된다 (build.gradle.kts:186-189).
           iOS      Podfile · Podfile.lock · Package.swift · Package.resolved ·
                    *.pbxproj 파일 자체가 없다 → 선언된 외부 SDK 0건.

EXIF       CAMERA 권한의 용도는 EarTagScannerScreen.kt — CameraX 프리뷰 +
           ML Kit 온디바이스 OCR. 이미지 파일 저장·업로드·multipart 코드 0건.
           ExifInterface · CGImageSource · kCGImagePropertyGPS 참조 0건.
           → 사진을 통한 GPS 유입 경로 없음. (iOS 촬영 코드 0건.)
```

★ **위치 권한이 선언되어 있지 않으면 OS 가 정밀 위치를 내주지 않는다.** 그래서 조건 5(SDK)
는 조건 4가 닫히는 순간 함께 닫힌다 — 어떤 SDK도 권한 없이 정밀 위치를 얻지 못한다.

★ iOS 저장소에 프로젝트 파일이 없다는 것은 **별건 관찰**이다. 이 저장소가 빌드·배포
가능한 상태인지는 V-11 의 범위가 아니며 여기서 판단하지 않는다.

```
판정   INSUFFICIENT_EVIDENCE  (조건 1·6 미완)
```

★ **`GPS_VERIFIED_UNUSED` 로 올리지 않는다.** 위 실측은 **현재 코드**에 수집 경로가 없다는
뜻이다. 과거 버전·수동 입력·마이그레이션 이전 데이터가 남았을 수 있고, 그것을 답하는 것은
조건 1·6 뿐이다.

★ 값이 하나라도 나오면 **V-11 REOPEN** — `[향후 수집]` 으로 자동 전환하지 않고
**현재 보유 사실 → 방침 정정 → 수집 경위·법적 근거·기존 이용자 영향** 을 별건으로 올린다.

---

## 4. `pigos_ro` — 생성하지 못했다

승인은 있으나 **세 가지가 막는다.**

| # | blocker | 내용 |
|---|---|---|
| B-1 | 접근 경로 없음 | DB 는 EC2 로컬 PostgreSQL 17.11 · 포트 5434 이고, `INFRA_DB_STRATEGY.md` 기준 **ufw 가 도커 브리지(172.17·172.18)만 허용 — 인터넷 비노출** 이다. 워크스테이션 `bjh` 실측: `psql` 없음 · `ssh` 클라이언트 없음 · `~/.ssh/config` 없음. `pigos_ro` 비밀번호는 서버 `~/.pgpass` 에만 있고 이 세션에 없다. **EC2 SSH 세션을 가진 사람만 실행할 수 있다** |
| B-2 | **`PIGOS_RO_AUDITABILITY_BLOCKER`** | 승인 조건에 "조회 로그 보존"이 있다. **read-only 롤 자체는 SELECT 감사 로깅을 보장하지 않는다.** PostgreSQL 기본값은 SELECT 를 기록하지 않으며, `log_statement='all'` 또는 `pgaudit` 가 필요하다. 현재 서버 설정을 확인할 수 없어 **조건 충족으로 처리하지 않는다** |
| B-3 | **승인된 grant 로는 V-11 을 못 푼다** | `KPI_K_LOOP` P-1 은 `GRANT SELECT (id, country, data_origin, data_classification, farm_scale) ON farms` 이다. **`gps_lat`·`gps_lng` 가 컬럼 목록에 없다.** 권한 확대는 승인 범위 밖 |

### 권고 — 권한 확대 없이 V-11 을 닫는 경로

`pigos_ro` 와 별개로, EC2 에서 기존 `sudo -u postgres psql` 경로로 **집계 한 줄**을 1회
실행하면 된다. 개인정보를 출력하지 않고 정수 두 개만 나온다.

```sql
SELECT count(*) FILTER (WHERE gps_lat IS NOT NULL) AS lat_rows,
       count(*) FILTER (WHERE gps_lng IS NOT NULL) AS lng_rows
FROM farms;
```

★ raw 좌표 출력 금지. 결과가 `0, 0` 이면 V-11 조건 1 충족 · 그 외면 REOPEN.
조건 6(backup·log)은 같은 세션에서 `~/pigos-backups/` 보존 여부와 함께 판단한다.

---

## 5. ★ H13 (4) 의 실제 적용 범위 — Brian 확인 필요 (OPEN)

**초판에서 "TH·VN 도 닫힌다"고 적었는데, 그것도 과소 보고였다.**
2026-09-10 기존 테스트 실측 결과 `_LAUNCH_ALLOWLIST` 는 **7개국**의 가입 판정을 바꾼다.

```
signup_blocked 가 바뀐 나라   BR · DE · GB · KR · MX · TH · VN
사유 코드                     LAUNCH_NOT_ENABLED (KR·CN 은 기존 코드 유지)
결재문이 명시한 범위          OTHER (= MX 등)
```

### 이것이 깨뜨리는 기존 기록

`_LAUNCH_ALLOWLIST` 도입 전후로 기존 테스트를 각각 돌려 **내 변경이 만든 실패만**
분리했다 (baseline = worktree 8fc382b).

```
변경 전부터 실패 (내 변경과 무관 · 별건)
  test_unsupported_country_purpose2::test_ac5_blocked_jurisdictions_gate_unchanged
  test_unsupported_country_purpose2::test_ac6b_only_other_group_changed_in_snapshot
  test_consent_plan::test_kr_anon_is_notice_not_toggle

이번 변경이 새로 깨뜨린 것 (5건)
  test_jurisdiction::test_eu_de_uses_eu_addendum_and_release_hold
  test_jurisdiction::test_gb_is_split_from_eu
  test_jurisdiction::test_th_paid_gate_and_override
  test_unsupported_country_purpose2::test_ac5b_unsupported_country_is_not_signup_blocked
  test_unsupported_country_purpose2::test_ac6_supported_countries_snapshot_unchanged
```

★ `test_ac5b_unsupported_country_is_not_signup_blocked` 는 **purpose2 의 기록된
수용 기준(AC5b)** 이다. "미지원 국가는 가입 차단하지 않는다" 가 먼저 결정되어
있었고, H13 (4) 는 그것을 뒤집는다.

### 갈리는 두 해석 — 어느 쪽인지는 Brian 이 정한다

```
해석 A (현재 구현)   allowlist 에 없으면 전부 차단
                     → BR·DE·GB·TH·VN 까지 닫힌다. R-10 은 부수적으로 해소된다
                     → AC5b 폐기 + EU/GB/BR/TH/VN 게이트 정책 변경을 함께 결정해야 한다

해석 B (좁은 읽기)   결재문이 적은 그대로 OTHER 그룹만 차단
                     → 기존 6개 법역 게이트는 손대지 않는다
                     → AC5b 는 여전히 뒤집힌다(OTHER 가 곧 AC5b 의 대상이므로).
                       다만 파장이 MX 등 OTHER 로 한정된다
```

★ **테스트를 고쳐서 초록으로 만들지 않았다.** 위 5건은 기록된 결정과 현재 코드가
어긋난다는 사실 그 자체이며, 그것을 지우는 것은 결정을 위조하는 것이다.
어느 해석인지 정해지면 (A) 기존 결정 문서에 supersede 기록을 남기고 테스트를
갱신하거나, (B) `_LAUNCH_ALLOWLIST` 판정을 `group == "OTHER"` 로 좁힌다.

### 5-1. ★ 전량 실측 — 실패는 5건이 아니라 12건이다 (2026-09-11)

위 §5 는 unit 테스트만 돌린 결과였다. 전량(1468 수집)을 돌리면 **12 failed · 1453
passed · 1 skipped · 2 xfailed** 다. 통합 테스트가 빠져 있었다.

★ **12건이 전부 같은 성격이 아니다.** 네 무리로 갈리고, 무리마다 A/B 해석에서
해야 할 일이 다르다.

```
[1] 결정 충돌 — A·B 어느 해석에서도 깨진다. purpose2 AC5b 를 H13 이 뒤집는다
    test_unsupported_country_purpose2::test_ac5b_unsupported_country_is_not_signup_blocked
    test_unsupported_country_purpose2::test_ac6_supported_countries_snapshot_unchanged
    test_country_entry_authority::test_unsupported_country_policy_is_unchanged
    test_publication_consent_gate::test_us_first_also_opens_every_country_without_an_addendum
      ★ 2026-09-10 에 "US 승인이 OTHER 를 함께 연다"를 고정하려고 쓴 테스트다.
        H13 (4) 가 정확히 그 동작을 바꿨으므로 깨지는 것이 맞다
    → 해석 확정 후: purpose2 결정문에 supersede 기록 + 테스트를 새 결정 기준으로 갱신

[2] 해석 A 에서만 깨진다 — B 면 코드를 OTHER 로 좁혀야 통과한다
    test_jurisdiction::test_eu_de_uses_eu_addendum_and_release_hold     (DE)
    test_jurisdiction::test_gb_is_split_from_eu                         (GB)
    test_jurisdiction::test_th_paid_gate_and_override                   (TH)
    test_country_entry_authority::test_us_account_br_farm_is_allowed_… (BR)
    test_consent_record_context::test_vn_transaction_matching_hidden_…  (VN)
    → A 면 [1] 과 같이 supersede · B 면 _LAUNCH_ALLOWLIST 판정을 group=="OTHER" 로 한정

[3] 픽스처 우연 — launch 정책과 무관. 통화·단위 파생을 CL·RU 로 검증하던 것
    test_onboarding_country::test_chile_farm_gets_clp_metric_santiago
    test_onboarding_country::test_russia_farm_gets_rub_moscow
    → 어느 해석이든 픽스처 국가를 allowlist 국가로 바꾸거나 LAUNCH_ 오버라이드 주입.
      ★ 테스트 의도(통화 파생)는 그대로다. 정책 테스트가 아니다

[4] 선존 — 이 변경 전부터 실패
    test_unsupported_country_purpose2::test_ac6b_only_other_group_changed_in_snapshot
```

★ **[3] 이 중요하다.** H13 이 **launch 정책과 무관한 테스트까지 깨뜨린다**는 것은,
allowlist 가 온보딩 픽스처의 기본 국가 선택을 전부 오염시킨다는 뜻이다. 앞으로
US 외 국가를 픽스처로 쓰는 모든 테스트가 같은 방식으로 깨진다 — `LAUNCH_{국가}`
오버라이드를 테스트 픽스처에 넣는 관례가 필요하다.

★ **`main` 이 빨간 상태로 커밋돼 있다.** 테스트를 초록으로 만들지 않은 판단은 맞다 —
다만 §0-2 기준으로 이것은 `STOP-on-FAIL` 이고, 해석 확정 전까지 **다른 배포·머지를
막는 상태**다. V-11 에 쓴 것과 같은 방식(`xfail` + 사유)이 [1]·[2] 에는 **해석
확정 후에야** 적용 가능하고, [3] 은 지금 고칠 수 있다.

### ★ 결재문 자체가 두 문장을 담고 있다

두 해석이 갈리는 원인은 구현이 아니다. `CEO_APPROVAL_REQUEST` 결재 1 (4) 행이
**한 칸 안에 A 와 B 를 함께 적었다.**

```
제목   "OTHER 기본 차단 + 국가별 개시 allowlist"                         → B
본문   "미국만 우선 허용"                                                → A
       "문서 세트 존재 여부와 개시 가능 여부를 별도 게이트로 관리"         → A
얻는 것 "세 상태가 분리됨"                                               → A
```

"미국만 우선 허용"은 문자 그대로 US 외 전부이고, "OTHER 기본 차단"은 범위를
OTHER 로 한정한다. **구현은 본문을 읽었고, B 는 제목을 읽었다.** 둘 다 결재문에
근거가 있다.

★ 그러므로 해석 확정의 **정본은 테스트도 코드도 아니라 결재문 (4) 행을 한 문장으로
고쳐 쓰는 것**이다. 그 뒤에 코드와 테스트가 따라간다.

### 두 해석의 실질 차이 — 언제 갈리나

BR·DE·GB·TH·VN 은 **B 여도 지금은 안 열린다** — addendum 이 전부 DRAFT 라 G-3 가
막는다. 차이는 **그 addendum 이 승인된 뒤**에 난다.

```
A   addendum 승인 + allowlist 등재  둘 다 있어야 열림   ← "세 상태 분리"
B   addendum 승인만 되면 열림                          ← 문서 완성 = 개시 허용 (6개국 한정)
```

B 는 결재문이 (4) 의 장점으로 적은 "세 상태 분리"를 **OTHER 에서만 실현하고
6개 법역에서는 포기**하는 안이다. 그게 의도라면 유효하나, "얻는 것" 칸과는 어긋난다.

**어느 쪽이든 A 정정 배포의 blocker 는 아니다** — 공개 방침 문안과 무관하다.
다만 **B 개시 배포 전에는 반드시 닫혀야 한다.**

---

## 6. 여전히 사람·변호사가 채워야 하는 것

```
변호사   D-13 (controller/processor) · Q-B (US 3종 최소 세트) · Q-A · Q-C · Q-E · Q-F · Q-G
         KR 법정 고지사항 충족 여부 (D-16 조건)
         침해통지 기한표 7개국 (2차 요청)

대표     H11 · H12 · H14 · H10 · H15 · T-8 · DPA-10~13 · P0 배포 승인
         서명 결재문 (이 문서의 구두 상태를 승격)

실측     V-11 조건 1·6 — EC2 SSH 세션 1회 (§4 집계 쿼리 + backups 보존 확인)
         R-08 숫자 · CN-1 · TH-5 · VN-5
         별첨 A 의 SIEM · IDS/WAF 미확인 2건
         T-6 잔여: 외부 보안점검 이력 · AWS Inspector/GuardDuty 활성 여부
```

---

## 7. 관련

```
docs/legal/CEO_APPROVAL_REQUEST_20260910.md      결재 요청 v4
docs/legal/DEPLOY_GATE_20260910.md               §6-0 배포 A/B · G-1a/G-1b
docs/legal/KNOWN_PUBLICATION_EXPOSURE.md         P1/P2 분리 · 격리 명세
docs/legal/DECISION_REGISTER.md                  D-16
docs/INFRA_DB_STRATEGY.md                        DB 노출 범위 (B-1 근거)
docs/runs/KPI_K_LOOP.md                          P-1 GRANT 컬럼 목록 (B-3 근거)
api/app/services/jurisdiction.py                 _LAUNCH_ALLOWLIST
api/app/services/terms_renderer.py               _GROUP_ADDENDUM
api/tests/unit/test_launch_allowlist_h13.py
api/tests/unit/test_addendum_map_parity_d16.py
api/tests/integration/test_public_legal_no_internal_markers.py
```
