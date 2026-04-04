import { API_BASE_URL, DASHBOARD_ADMIN_TOKEN, IS_PROD_ENV } from './env';

export interface InitResponse {
  code: string;
  data: {
    session_id: string;
    user_id?: string;
    address_name: string;   // 逆地理编码后的地名，供 LocationBar 展示
    fallback_used: boolean;
  };
}

export interface AuthAnonymousResponse {
  code: string;
  data: {
    user_id: string;
    is_new: boolean;
    expires_at?: string;
  };
}

export interface ResolveLocationResponse {
  code: string;
  data: {
    location: string;
    address_name: string;
    fallback_used: boolean;
    used_default: boolean;
  };
}

export interface Candidate {
  candidate_id: string;
  name: string;
  type: string;
  eta_min: number;
  distance_m: number;
  transport_mode?: string;
  budget_text: string;
  ai_judgement: string;
  risk_label?: string;
}

export interface DashboardMetrics {
  period_days: number;
  sessions: number;
  picks: number;
  completion_rate: number | null;
  nav_rate: number | null;
  redraw_rate: number | null;
  persona_rate: number | null;
  feedback_rate: number | null;
  total_history: number;
}

export interface HistoryItem {
  pick_id: string;
  name: string;
  timestamp: string;
  conditions: string;
  satisfaction: number;
  went?: boolean;
  title?: string;
  content?: string;
  tags?: string[];
  actual_cost?: number | null;
  transport_used?: string | null;
}

export interface FeedbackSubmitPayload {
  sessionId: string;
  pickId: string;
  userId?: string;
  persona?: string;
  went: boolean;
  satisfaction: number;
  actualCost?: number;
  title?: string;
  content?: string;
  tags?: string[];
  transportUsed?: string;
}

const REQUEST_TIMEOUT_MS = IS_PROD_ENV ? 65000 : 12000;

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS);
  const requestId = `web_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
  const headers = new Headers(init?.headers);
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  headers.set('X-Request-Id', requestId);

  try {
    const res = await fetch(`${API_BASE_URL}${url}`, {
      ...init,
      headers,
      credentials: 'include',
      signal: ctrl.signal,
    });
    if (!res.ok) {
      throw new ApiError(`HTTP_${res.status}`, res.status);
    }
    return res.json();
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError('HTTP_TIMEOUT', 408);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  authAnonymous(userId?: string) {
    return request<AuthAnonymousResponse>('/auth/anonymous', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId }),
    });
  },

  resolveLocation(location?: string) {
    return request<ResolveLocationResponse>('/location/resolve', {
      method: 'POST',
      body: JSON.stringify({ location }),
    });
  },

  initRecommendation(prompt: string, location?: string, userId?: string) {
    return request<InitResponse>('/recommend/init', {
      method: 'POST',
      body: JSON.stringify({ prompt, location, user_id: userId }),
    });
  },

  getCandidates(sessionId: string) {
    return request<{ code: string; data: { candidates: Candidate[]; summary: string; fallback_used: boolean } }>(
      '/recommend/candidates',
      {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, limit: 10 }),
      },
    );
  },

  pick(sessionId: string) {
    return request<{ code: string; data: { pick_id: string; picked: { candidate_id?: string; name: string; type: string; distance_m?: number; eta_min: number; transport_mode?: string; budget_text: string; reason: string; nav_url?: string; location?: string }; fallback_used: boolean } }>(
      '/recommend/pick',
      {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, strategy: 'weighted_random', temperature: 1.2 }),
      },
    );
  },

  personaReview(sessionId: string, pickId: string, persona: string) {
    return request<{ code: string; data: { persona: string; review: string; risk: string; conclusion: string; summary: string; slices: import('../types').PersonaSlice[]; fallback_used: boolean } }>(
      '/persona/review',
      {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, pick_id: pickId, persona }),
      },
    );
  },

  submitFeedback(payload: FeedbackSubmitPayload) {
    return request<{ code: string; data: { feedback_id: string } }>('/feedback/submit', {
      method: 'POST',
      body: JSON.stringify({
        session_id: payload.sessionId,
        pick_id: payload.pickId,
        user_id: payload.userId,
        persona: payload.persona,
        went: payload.went,
        satisfaction: payload.satisfaction,
        actual_cost: payload.actualCost,
        title: payload.title,
        content: payload.content,
        tags: payload.tags || [],
        transport_used: payload.transportUsed,
      }),
    });
  },

  getHistory(userId?: string) {
    const qs = userId ? `?page=1&page_size=20&user_id=${encodeURIComponent(userId)}` : '?page=1&page_size=20';
    return request<{ code: string; data: { list: HistoryItem[] } }>(
      `/history/list${qs}`,
    );
  },

  inspire() {
    return request<{ code: string; data: { prompt: string } }>('/inspire');
  },

  getDashboardMetrics(days = 7) {
    return request<{ code: string; data: DashboardMetrics }>(`/dashboard/metrics?days=${days}`, {
      headers: DASHBOARD_ADMIN_TOKEN ? { 'X-Admin-Token': DASHBOARD_ADMIN_TOKEN } : undefined,
    });
  },
};
