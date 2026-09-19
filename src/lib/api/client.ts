import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

// 기본 빈 문자열 = 상대경로(같은 출처) → Next 서버 rewrites가 백엔드로 프록시.
// 브라우저가 LAN IP를 직접 안 잡아도 돼 PC/폰/VPN 무관하게 안정적.
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// ── 클라이언트 신원 헤더 ──────────────────────────────────────────────────────
// 서버가 어느 플랫폼·어느 버전이 붙어 있는지 관측할 수 있게 한다.
// ★ 지금은 송출·관측 단계다. 서버는 이 값으로 차단하지 않는다.
//   min_supported_version 게이트는 Web·Android·iOS 세 곳이 전부 송출하고
//   서버가 실제 수신을 확인한 뒤에 별도로 켠다 — 역순으로 켜면 정상 클라이언트가 막힌다.
//   docs/product/PIGOS_PRODUCT_IMPLEMENTATION_HANDOFF.md §12-1
export const CLIENT_PLATFORM = "web";
export const CLIENT_APP_VERSION = process.env.NEXT_PUBLIC_APP_VERSION ?? "0.0.0-dev";

// ── Request: inject Authorization header ─────────────────────────────────────
// Lazy import to avoid circular dependency (store imports client, client imports store)
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  config.headers["X-PigOS-Platform"] = CLIENT_PLATFORM;
  config.headers["X-PigOS-App-Version"] = CLIENT_APP_VERSION;
  if (typeof window !== "undefined") {
    try {
      const raw = localStorage.getItem("pigos-auth");
      if (raw) {
        const { state } = JSON.parse(raw) as { state: { accessToken: string | null } };
        if (state?.accessToken) {
          config.headers.Authorization = `Bearer ${state.accessToken}`;
        }
      }
    } catch {
      // Corrupt storage — handled by 401 response interceptor
    }
  }
  return config;
});

// ── Response: 401 refresh, 402 upgrade modal ──────────────────────────────────
let _refreshing: Promise<string> | null = null;

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // 401 → attempt token refresh once
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;

      if (!_refreshing) {
        _refreshing = _doRefresh().finally(() => { _refreshing = null; });
      }

      try {
        const newToken = await _refreshing;
        original.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(original);
      } catch {
        _clearAuth();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
      }
    }

    // 402 → open upgrade modal
    if (error.response?.status === 402) {
      if (typeof window !== "undefined") {
        // Dynamic import to avoid circular dep
        import("@/store/ui.store").then(({ useUiStore }) => {
          useUiStore.getState().openUpgradeModal(
            (error.response?.data as { code?: string })?.code
          );
        });
      }
    }

    return Promise.reject(error);
  }
);

async function _doRefresh(): Promise<string> {
  let refreshToken: string | null = null;
  try {
    const raw = localStorage.getItem("pigos-auth");
    if (raw) {
      const { state } = JSON.parse(raw) as { state: { refreshToken: string | null } };
      refreshToken = state?.refreshToken ?? null;
    }
  } catch {
    throw new Error("No refresh token");
  }

  if (!refreshToken) throw new Error("No refresh token");

  const { data } = await axios.post<{ access_token: string }>(
    `${API_BASE}/api/v1/auth/refresh`,
    { refresh_token: refreshToken }
  );

  // Update stored access token (localStorage: 요청 인터셉터가 직접 읽음)
  try {
    const raw = localStorage.getItem("pigos-auth");
    if (raw) {
      const parsed = JSON.parse(raw) as { state: Record<string, unknown> };
      parsed.state.accessToken = data.access_token;
      localStorage.setItem("pigos-auth", JSON.stringify(parsed));
    }
  } catch {
    // Ignore storage errors
  }
  // Zustand 인메모리 상태도 동기화 — 안 하면 useAuthStore(s=>s.accessToken) 구독 컴포넌트가
  // 새로고침 전까지 만료 토큰을 들고 있음(Finding 4). 순환참조 회피 위해 지연 import.
  if (typeof window !== "undefined") {
    import("@/store/auth.store").then(({ useAuthStore }) =>
      useAuthStore.getState().setAccessToken(data.access_token),
    ).catch(() => { /* ignore */ });
  }

  return data.access_token;
}

function _clearAuth() {
  try {
    const raw = localStorage.getItem("pigos-auth");
    if (raw) {
      const parsed = JSON.parse(raw) as { state: Record<string, unknown> };
      parsed.state.accessToken = null;
      parsed.state.refreshToken = null;
      parsed.state.user = null;
      localStorage.setItem("pigos-auth", JSON.stringify(parsed));
    }
  } catch {
    localStorage.removeItem("pigos-auth");
  }
  // 세션쿠키도 삭제 — 안 지우면 middleware가 /login→/ 로 되튕겨 무한 새로고침 루프 발생.
  if (typeof document !== "undefined") {
    document.cookie = "pigos_session=; path=/; max-age=0; SameSite=Lax";
  }
  // Zustand 인메모리 상태도 비움(localStorage만 비우면 isAuthenticated()가 잠깐 true 유지).
  if (typeof window !== "undefined") {
    import("@/store/auth.store").then(({ useAuthStore }) =>
      useAuthStore.getState().clearAuth(),
    ).catch(() => { /* ignore */ });
  }
}
