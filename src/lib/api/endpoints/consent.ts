import { apiClient } from "@/lib/api/client";
import type {
  ConsentStatus, RecordConsentRequest, SignupPlan, WithdrawRequest,
} from "@/types/api.types";

// 동의 인프라 — 가입/설정 플랜 조회, 기록, 현재상태, 철회. (TERMS_DISPLAY §7)
export const consentApi = {
  signupPlan: (params: {
    selected_country: string; farm_country?: string; farm_state?: string;
    lang?: string; include_body?: boolean;
  }) => apiClient.get<SignupPlan>("/api/v1/consent/signup-plan", { params }).then((r) => r.data),

  /**
   * 동의 기록. 인증 필요.
   *
   * ★ accessToken 을 명시로 받을 수 있다 — 가입 직후에는 아직 auth store 에
   *   토큰을 저장하지 않기 때문이다(LEGAL-P0-WEB-CONSENT-FAIL-CLOSED).
   *   동의 기록이 성공해야 로그인 상태를 확정하므로, 그 전까지 토큰은
   *   이 호출에만 임시로 쓴다. 생략하면 인터셉터가 store 값을 쓴다.
   */
  record: (body: RecordConsentRequest, accessToken?: string) =>
    apiClient
      .post<ConsentStatus[]>("/api/v1/consent/record", body,
        accessToken ? { headers: { Authorization: `Bearer ${accessToken}` } } : undefined)
      .then((r) => r.data),

  current: (farm_id?: string) =>
    apiClient.get<ConsentStatus[]>("/api/v1/consent/current", { params: farm_id ? { farm_id } : {} }).then((r) => r.data),

  withdraw: (body: WithdrawRequest) =>
    apiClient.post<ConsentStatus>("/api/v1/consent/withdraw", body).then((r) => r.data),
};
