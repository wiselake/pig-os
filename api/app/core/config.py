from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "postgresql+asyncpg://pigos:pigos@localhost:5432/pigos"

    # DB 커넥션 풀 — Supabase Supavisor 세션 모드 한도가 pool_size:15(동시 클라이언트)다.
    # api·worker 가 같은 엔진 설정을 공유하므로 컨테이너별 합이 그 한도를 넘으면 안 된다.
    # 넘으면 EMAXCONNSESSION / ECHECKOUTTIMEOUT 이 나고, 마이그레이션·백업·모니터링이
    # 들어갈 자리도 사라진다(2026-08-20 프로덕션 마이그레이션 실패의 실제 원인).
    # 예산: api 최대 6(4+2) · worker 최대 2(1+1, compose env 로 하향) = 8, 여유 7.
    # 대시보드에서 풀러 pool_size 를 올리면 코드 수정 없이 env 로 상향 가능.
    # pool_size = 상시 유지 커넥션. 이게 작으면 초과 요청마다 새로 연결하는데,
    # 풀러 경유 신규 연결은 수 초가 걸린다(2026-08-21 로그인 7.4s 회귀의 원인).
    # max_overflow 는 임시 커넥션이라 반환 후 닫힌다 — 지연 해소에 도움이 안 된다.
    db_pool_size: int = 4
    db_max_overflow: int = 2
    db_pool_timeout: int = 10        # 슬롯 대기 상한(초) — 매달리지 않고 빠르게 실패
    db_pool_recycle: int = 3600      # 묵은 커넥션 방지. 짧으면 강제 재연결이 잦아 느려진다

    # 대시보드 응답 캐시 TTL(초). 0 이면 캐시 끔.
    # 30초면 화면 반복 조회는 즉시 응답하고, 입력 직후 최신값도 곧 반영된다.
    # 이벤트 입력 시에는 cache.invalidate_farm 으로 즉시 무효화한다.
    dashboard_cache_ttl: int = 30

    # DB 커넥션 keepalive 주기(초). 0 이면 끔.
    # 풀러가 유휴 커넥션을 끊으면 재수립에 수 초가 걸려 응답이 튄다(2026-08-25).
    # 풀러 유휴 타임아웃보다 짧아야 의미가 있다.
    db_keepalive_interval: int = 20
    redis_url: str = "redis://localhost:6379/0"

    # ── 가입 남용 방지 (rate_limit.py) ────────────────────────────────────────
    # ★ 제품 정책이 아니라 **운영 기본값**이다. 정상 농가가 막히지 않는 선으로 두고,
    #   실제 트래픽을 보고 조정한다. 0 이하 = 비활성(개발·테스트).
    #   근거: docs/runs/RATE_LIMIT_POLICY.md
    rate_limit_signup_per_hour: int = 5      # 한 출처에서 시간당 가입 시도
    rate_limit_auth_per_minute: int = 20     # 로그인·토큰·비밀번호 재설정
    secret_key: str = "change-me-in-production-at-least-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    environment: str = "development"
    cors_origins: list[str] = [
        "https://pigos.io",
        "https://app.pigos.io",
        "https://admin.pigos.io",  # 운영자 콘솔 — 누락 시 admin API 호출 CORS 차단
    ]

    # Supabase (파일럿 신청용 + 프로덕션 DB)
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # FCM 푸시 (G1) — 둘 다 설정돼야 푸시 전송, 아니면 graceful skip
    fcm_project_id: str = ""
    # 서비스 계정 JSON 경로 (google-auth가 읽음). 미설정 시 푸시 비활성.
    fcm_credentials_path: str = ""

    # AWS SES 이메일 발송(권장, AWS 네이티브 — 인프라 서울리전). ses_from_email(SES 인증 발신주소)
    # 설정 시 SES 우선. AWS 자격증명은 표준 체인(AWS_ACCESS_KEY_ID/SECRET env 또는 EC2/ECS IAM 롤)으로
    # 해석 — 코드에 비밀값 0. pigsignal-collector의 SES 설정과 동일 컨벤션(AWS_REGION/SES_FROM_EMAIL).
    aws_region: str = "ap-northeast-2"
    ses_from_email: str = ""

    # SMTP 이메일 발송 (SES 미설정 시 폴백). host+user+password 모두 설정돼야 전송, 아니면 graceful
    # skip(로그 폴백) — 비밀값은 env로만 주입(코드에 하드코딩 금지).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""          # 발신 주소(미설정 시 smtp_user 사용)
    smtp_use_tls: bool = True    # 587 STARTTLS
    # 이메일 내 링크용 프론트 베이스 URL (예: https://app.pigos.io)
    app_base_url: str = "http://localhost:3000"

    # KPI Governance 3-table benchmark 연결 (handoff/KPI_GOVERNANCE_v3.1.md).
    # True: Rule Engine이 governance resolver만 사용(검증 안 된 benchmark는 발화 금지+insufficient).
    # False(기본): 기존 default_metric_values 경로 유지(롤백 전용·현행 동작). 운영 전환 전까지 False.
    use_governance_benchmarks: bool = False

    # KR 가입 정책: KR은 공개 마케팅 타겟 아님(레퍼런스 전용) → 운영은 기본 가입 차단.
    # True로 두면 KR 가입 허용(대표 확인·검토용 환경에서만 env로 켬). 클라이언트가 못 바꿈(서버 env).
    allow_kr_signup: bool = False

    # QBridge CRM 양방향 연동 (docs: QBridge repo docs/integrations/pigos.md).
    #  - qbridge_url + qbridge_inbound_token: 문의 발신(A). 미설정 시 아웃바운드 no-op.
    #  - qbridge_service_token: 답변 수신(B) 서비스토큰. 미설정 시 인바운드 503.
    qbridge_url: str = ""
    qbridge_inbound_token: str = ""
    qbridge_service_token: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def qbridge_outbound_configured(self) -> bool:
        return bool(self.qbridge_url and self.qbridge_inbound_token)

    @property
    def ses_configured(self) -> bool:
        """SES 인증 발신주소가 있으면 SES 사용(AWS 자격증명은 표준 체인/IAM 롤로 런타임 해석)."""
        return bool(self.ses_from_email)

    @property
    def smtp_configured(self) -> bool:
        """host+user+password 다 있어야 실제 발송. 하나라도 없으면 로그 폴백."""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    @property
    def sync_database_url(self) -> str:
        """Alembic needs synchronous URL."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")


settings = Settings()
