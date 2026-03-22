export interface InitResponse {
  code: string;
  data: {
    session_id: string;
    address_name: string;   // 逆地理编码后的地名，供 LocationBar 展示
    fallback_used: boolean;
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

const API_PREFIX = '/api/v1';

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_PREFIX}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) throw new Error(`HTTP_${res.status}`);
  return res.json();
}

export const api = {
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
    return request<{ code: string; data: { pick_id: string; picked: { candidate_id?: string; name: string; type: string; distance_m?: number; eta_min: number; transport_mode?: string; budget_text: string; reason: string; nav_url?: string }; fallback_used: boolean } }>(
      '/recommend/pick',
      {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, strategy: 'weighted_random', temperature: 0.7 }),
      },
    );
  },

  personaReview(sessionId: string, pickId: string, persona: string) {
    return request<{ code: string; data: { persona: string; review: string; risk: string; conclusion: string; fallback_used: boolean } }>(
      '/persona/review',
      {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, pick_id: pickId, persona }),
      },
    );
  },

  submitFeedback(sessionId: string, pickId: string, userId?: string, persona?: string, satisfaction?: number, actualCost?: number) {
    return request<{ code: string; data: { feedback_id: string } }>('/feedback/submit', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        pick_id: pickId,
        went: true,
        satisfaction: satisfaction ?? 4,
        user_id: userId,
        persona,
        actual_cost: actualCost,
      }),
    });
  },

  getHistory() {
    return request<{ code: string; data: { list: Array<{ pick_id: string; name: string; timestamp: string; conditions: string; satisfaction: number }> } }>(
      '/history/list?page=1&page_size=20',
    );
  },
};
