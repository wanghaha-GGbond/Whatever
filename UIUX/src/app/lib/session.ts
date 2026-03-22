export const sessionStore = {
  setSessionId(sessionId: string) {
    localStorage.setItem('p003_session_id', sessionId);
  },
  getSessionId() {
    return localStorage.getItem('p003_session_id') || '';
  },
  setPickId(pickId: string) {
    localStorage.setItem('p003_pick_id', pickId);
  },
  getPickId() {
    return localStorage.getItem('p003_pick_id') || '';
  },
  setPicked(picked: object) {
    localStorage.setItem('p003_picked', JSON.stringify(picked));
  },
  getPicked<T>(): T | null {
    const raw = localStorage.getItem('p003_picked');
    if (!raw) return null;
    try { return JSON.parse(raw) as T; } catch { return null; }
  },
  setCandidatePool(pool: object[]) {
    localStorage.setItem('p003_candidate_pool', JSON.stringify(pool));
  },
  getCandidatePool<T>(): T[] {
    const raw = localStorage.getItem('p003_candidate_pool');
    if (!raw) return [];
    try {
      const data = JSON.parse(raw);
      return Array.isArray(data) ? (data as T[]) : [];
    } catch {
      return [];
    }
  },
  getDeviceId(): string {
    let id = localStorage.getItem('p003_device_id');
    if (!id) {
      id = `dev_${Math.random().toString(36).slice(2, 12)}`;
      localStorage.setItem('p003_device_id', id);
    }
    return id;
  },
};
