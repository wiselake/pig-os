"""로케일 카탈로그는 SUPPORTED_LOCALES 를 정확히 채워야 한다.

## 왜

`app/engine/i18n.py:4` 는 이미 "새 룰을 추가하면 SUPPORTED_LOCALES 전부를 채워야
한다"고 적어두었다. **적어두기만 했다.** 프론트는 `src/tests/i18n.test.ts` 가 키
파리티를 강제하는데 백엔드에는 대응물이 없었고, 그 사이로 두 방향의 이탈이 생겼다.

    llm_renderer.py   주석은 "7개 로케일" 인데 dict 에는 ru 포함 8개   → 초과
    public_notice.py  ko·en 만                                        → 부족

규율은 있는데 강제가 없는 상태였다 — Node 핀이 선언만 있고 실행이 따르지 않던 것과
같은 모양이다(`docs/runs/RUN_COMMON_RULES.md`).

## ru 가 없는 것은 누락이 아니라 결정이다

`SUPPORTED_LOCALES` 에 ru 는 **의도적으로 없다.** CIS 는 리서치·부속조항이 미비해
아직 대상 시장이 아니고(CLAUDE.md 타겟 시장), 백엔드 카탈로그를 러시아어로 채우면
그것이 곧 "러시아어 서비스 제공 준비됨"의 코드 상 표명이 된다.

그래서 이 테스트는 ru 를 **넣어도 실패**한다. 빠뜨려서 실패하는 것과 같은 무게로
다룬다 — 지원 범위는 우연히 늘어나면 안 되는 값이다.

※ 프론트에는 ru 로케일이 존재한다(UI 8개). 그 노출을 유지할지는 사람 결정으로
   `docs/legal/HUMAN_INPUT_QUEUE.md` 에 등록돼 있다.
"""
from __future__ import annotations

from app.engine.i18n import SUPPORTED_LOCALES
from tests.locale_catalogs import iter_locale_dicts

REQUIRED = frozenset(SUPPORTED_LOCALES)

# ── 명시적 예외 ───────────────────────────────────────────────────────────────
# 가드를 느슨하게 만드는 대신 예외를 코드에 남긴다. 목록에 있는 것만 봐주고,
# 왜 봐주는지를 여기서 읽을 수 있어야 한다.
ALLOWLIST: dict[str, str] = {
    # 공개 게시용 개인정보 처리방침. 런타임 UI 문구가 아니라 **게시 문서**이고,
    # 게시 언어 세트는 법정 요건(BR pt-BR · TH th · VN vi)에 따라 별도로 정해진다.
    # 현재 ko·en 뿐이며 그 격차 자체가 대표 결정 안건이다
    # (HUMAN_INPUT_QUEUE H13 CURRENT_PUBLICATION_SET 의 입력).
    # ★ 이 예외는 "괜찮다"는 뜻이 아니라 "여기서 판정할 문제가 아니다"라는 뜻이다.
    "app/services/public_notice.py": "게시 문서 — 언어 세트는 법정 요건이 정한다 (H13)",
}


def test_scan_is_not_empty() -> None:
    """스캔이 조용히 0건이 되면 가드가 통과하는 게 아니라 사라진 것이다."""
    assert len(iter_locale_dicts()) > 100


def test_every_catalog_covers_supported_locales_exactly() -> None:
    offenders: list[str] = []
    for cat in iter_locale_dicts():
        if cat.path in ALLOWLIST:
            continue
        if cat.locales == REQUIRED:
            continue
        missing = sorted(REQUIRED - cat.locales)
        extra = sorted(cat.locales - REQUIRED)
        offenders.append(
            f"{cat.path}:{cat.lineno}  missing={missing or '-'}  extra={extra or '-'}"
        )
    assert offenders == [], (
        "로케일 카탈로그가 SUPPORTED_LOCALES 와 어긋난다 "
        f"(required={sorted(REQUIRED)}):\n" + "\n".join(offenders)
    )


def test_allowlist_entries_still_exist() -> None:
    """예외가 대상 소멸 후에도 남아 조용히 커버리지를 갉아먹지 않도록."""
    seen = {cat.path for cat in iter_locale_dicts()}
    stale = sorted(set(ALLOWLIST) - seen)
    assert stale == [], f"ALLOWLIST 에 더 이상 존재하지 않는 항목이 있다: {stale}"
