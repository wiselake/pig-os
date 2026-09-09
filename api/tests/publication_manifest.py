"""테스트용 게시 문서 상태 조작 — G-3 게이트와 함께 쓴다.

`assert_publication_approved`(G-3)가 들어오면서, 계정을 만드는 모든 테스트가
게시 상태에 의존하게 됐다. 실제 `manifest.json` 은 현재 8건 전부
`DRAFT_LAWYER_PENDING` 이므로, 아무 조치 없이는 가입을 쓰는 통합 테스트가 전부
451 로 막힌다(2026-09-09 실측: 40건).

그래서 통합 테스트의 **기본값은 승인본**이다(`tests/integration/conftest.py` 의
autouse 픽스처). 게이트 자체를 검증하는 파일만 실제 manifest 를 쓴다.

★ 이 판단의 근거: 게이트는 **일시 상태**다. 문서가 승인되면 사라진다. 다른 기능의
  테스트가 그 일시 상태에 묶이면, 승인 시점에 40건이 다시 흔들린다. 각 테스트는
  자기가 검증하는 것만 전제로 삼아야 한다.

※ `test_` 로 시작하지 않으므로 pytest 가 테스트 모듈로 수집하지 않는다.
"""
from __future__ import annotations

APPROVED_STATUS = "APPROVED"


def approved(raw: dict) -> dict:
    """같은 manifest 를 status 만 승인본으로 바꿔 돌려준다.

    문서 내용·언어·버전 구성은 건드리지 않는다 — 게이트가 보는 것은 status 뿐이고,
    다른 필드를 함께 바꾸면 이 헬퍼가 무엇을 검증하는지 흐려진다.
    """
    docs = raw.get("documents")
    if isinstance(docs, dict):
        return {
            **raw,
            "documents": {
                k: ({**v, "status": APPROVED_STATUS} if isinstance(v, dict) else v)
                for k, v in docs.items()
            },
        }
    # documents 래퍼가 없는 형태(문서가 최상위 키)도 지원한다.
    return {
        k: ({**v, "status": APPROVED_STATUS} if isinstance(v, dict) and "status" in v else v)
        for k, v in raw.items()
    }
