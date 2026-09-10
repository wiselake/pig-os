# DECISION_REGISTER v1.2
## PigOS 글로벌 약관 — 의사결정 레지스터 (2026-07-21)

> 성격: 각 결정은 변호사 의견 선행 후 대표 승인. 옵션 뒤 괄호는 리서치 근거 문서.
> 상태: OPEN(미결) / PROPOSED(초안 반영값 있음 — 초안에는 [D-xx] 표기) / DECIDED

| ID | 결정 사항 | 옵션 | 초안 반영값(PROPOSED) | 승인자 | 상태 |
|---|---|---|---|---|---|
| D-01 | 목적② 익명·집계 통계의 글로벌 설계 — 동의 토글 vs 법적근거 분기 | (a) 전세계 옵트인 토글 (b) 국가별 분기: EU/GB·BR=LI+고지·이의권, KR=제58조의2 익명정보+고지·제외요청, US=비식별+고지, CN/VN/TH=현지 요건 (c) 전세계 LI/고지+이의권 | **(b) 국가별 분기** — EU 리서치가 동의 프레임 자초 리스크 지적, KR은 현행 선례 유지 (GB_EU §2·3, KR §2) | 대표 (법무 선행) | **BUSINESS_APPROVED · COUNSEL_PENDING** (2026-07-21, 조건부†) |
| D-02 | 목적③④⑤ (AI 학습·기업 연구·리드 제공) | 옵트인(기본 OFF) 외 대안 없음 확인됨 — 리드⑤는 익명 우회 불가(4개국 HIGH) | **별도 옵트인, 기본 OFF, 목적별 개별 토글** | 대표 | **BUSINESS_APPROVED · COUNSEL_PENDING** (2026-07-21, 조건부†) |
| D-03 | "20년 보유" 문구 처리 | (a) 유지 (b) 숫자 삭제 + "탈퇴 전 비가역 익명화 완료된 통계 산출물은 개인정보 아님·존속 가능" 구조로 재작성, 기간은 내부 데이터 보유정책에서만 관리 | **(b)** — 7개국 공통 결론 | 대표 (법무 선행) | **BUSINESS_APPROVED · COUNSEL_PENDING** (2026-07-21, 조건부†) |
| D-04 | "기제공분 소급회수 불가" 적용 범위 | (a) 현행 유지 (b) 적용 대상을 "철회 전 적법 처리 + 이미 제3자 제공 + 비가역 익명화 완료 산출물"로 한정, 개인정보·가명정보에는 부적용 명시 | **(b)** | 대표 (법무 선행) | **BUSINESS_APPROVED · COUNSEL_PENDING** (2026-07-21, 조건부†) |
| D-05 | 글로벌 최소 코호트 (Release Gate) | 후보: 기본 k=10, 세분화 상품 k=20 + 지배율 통제(단일 70%/상위2 85%) — `INTERNAL_POLICY_PROPOSAL`, 법정 수치 아님 | 후보값 기재, **확정은 변호사+통계 검증 후** (ANONYMIZATION_AND_RELEASE_STANDARD) | 대표 (법무+데이터 선행) | OPEN |
| D-06 | KR 코호트 5 → 글로벌 값으로 상향 통일 여부 | (a) KR 5 유지 + 글로벌 상향(이원) (b) 전사 통일 상향 | 이원 기준 시 정합 설명 부담 (스냅샷 파생 결정 항목) | 대표 | OPEN |
| D-07 | 중국 진입 구조 | (a) 직접 (b) 현지 법인 (c) 파트너 라이선스 (d) CN 데이터 PigSignal 편입 금지 (e) 질병 데이터 수집·판매 제외 | **HOLD — 부속조항으로 해소 불가** (CN_legal §8). (d)(e)는 어느 구조든 기본 채택 검토 | 대표 (현지 법무 필수) | OPEN |
| D-08 | 베트남 출시 게이트 | TIA 서류·데이터 서비스 라이선스 해당성·현지화 해석 확인 전 조건부 | 확인 전 유료·마케팅 보류 | 대표 | OPEN |
| D-09 | 태국 출시 게이트 | 현지 대리인(§37(5) 무한책임)·Thai SCC 체결 전 조건부 | 확인 전 유료·본격 마케팅 보류 | 대표 | OPEN |
| D-10 | B2B 콜드 이메일 채널 | KR·DE·DK·IT·PL 등 옵트인 국가 발송 금지, CAN-SPAM권만 옵트아웃 운영 or 전면 동의 기반 전환 | **국가 코드 게이팅 + KR 즉시 중단** (KR R1 HIGH) | 대표 | PROPOSED |
| D-11 | (기존 등록) KR 피그플랜 옵트아웃 유지 + 글로벌 옵트인 분기 vs 전사 통일 | D-01과 통합 — F5(게시본 상충·운영 미확인) 해소가 선행 조건 | — | 대표 (법무 선행) | OPEN → D-01로 흡수 |
| D-12 | 데이터 수익 배분(농장 share) 약관 포함 여부 | 확정 모델이면 계산·지급·세금·최소액·취소 조항 필요, 미확정이면 약관에서 제외 | 사업 결정 대기 | 대표 | OPEN |
| D-13 | controller/processor 역할 확정 (처리 유형별) | 가입·결제·보안=WiseLake controller / 기업 입력 직원·계약농가=고객 controller·WiseLake processor 가능 / PigSignal=WiseLake (공동)controller | B2B DPA 신설 반영, 확정은 변호사 | 대표(법무 선행) | OPEN |
| D-14 | 조직의 계약농가·직원 대리 동의 범위 | 마스터 제4조⑥ 한정 조항 + authorized_consent_actor 요건 | 한정안 반영 | 대표(법무 선행) | PROPOSED |
| D-15 | 유료/무료 기능 경계 확정 (조기경보 무료 여부 등) | 화면·가격표 표시 기준으로 완화, 실제 경계는 사업 결정 | 문구 완화 반영 | 대표(사업) | OPEN |
| D-16 | KR·CN 국가별 부속조항 파일을 두지 않는 문서 구조 | (a) 6개국(US·EU·GB·BR·TH·VN)만 부속조항 유지 (b) KR·CN 부속조항 신설 | **(a)** — KR: PigOS 비대상(A-rule, signup_blocked)이며 한국법 적용은 마스터 준거법 조항과 목적② KR 분기가 흡수. CN: 진입 구조 미결(D-07)이라 부속조항이 성립하지 않음. 코드 `jurisdiction._ADDENDUM` · `terms_renderer._GROUP_ADDENDUM` 양쪽에 `None` 명시 | 대표 | **APPROVED_VERBAL** (2026-09-10 구두, 서명본 대기) — ★ **KR 법정 고지사항이 글로벌 방침·마스터에 충분히 반영되어 별도 부속조항이 불필요하다는 법률 판단은 포함하지 않는다. COUNSEL_PENDING** (1차 자문 Q-B 부속 질의) |

> † D-01~D-04는 2026-07-21 대표 승인으로 설계 기준 확정. 단 원래 "법무 의견 선행" 조건 항목이므로, LAWYER_BRIEF 회신에서 반대 의견이 나오는 경우 해당 결정은 자동 재개(REOPEN)한다. D-01은 F5(게시본·운영 불일치)·V1(동의 UI·로그 실사) 해소 병행 필요.

## 선행 의존 관계

- D-01/D-04: DECIDED(조건부) — V1(동의 UI·로그 확인) + F5 해소는 이행 조건으로 유지
- D-05/D-06 확정 ← ANONYMIZATION_AND_RELEASE_STANDARD 통계 검증 + 변호사 의견
- 최종 약관 게시 ← D-05/D-06 DECIDED + LAWYER_BRIEF 회신 (D-01~D-04 확정 완료)

## 상태 enum (OPEN_QUESTIONS와 공유)
PROPOSED / BUSINESS_APPROVED / COUNSEL_PENDING / TECHNICAL_VERIFICATION_PENDING / IMPLEMENTATION_PENDING / BLOCKED / REOPENED / CLOSED / NOT_APPLICABLE.
D-01~D-04 = BUSINESS_APPROVED + COUNSEL_PENDING → OVERALL BLOCKED(회신 후 CLOSED, 반대 시 REOPENED). 검토자는 재상정 대신 REOPEN 후보로만 표기.
