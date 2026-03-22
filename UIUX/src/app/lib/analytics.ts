/**
 * 轻量级埋点客户端。
 * 事件先入本地队列，每 3 秒或队列满 10 条时批量上报。
 * 上报失败静默忽略，不影响用户体验。
 */
import { API_BASE_URL } from './env';

interface TrackEvent {
  event_name: string;
  session_id?: string;
  user_id?: string;
  properties?: Record<string, unknown>;
  ts: string;
}

const FLUSH_INTERVAL_MS = 3000;
const FLUSH_BATCH_SIZE = 10;

let queue: TrackEvent[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;
let pagehideBound = false;

function flush() {
  if (queue.length === 0) return;
  const batch = queue.splice(0, queue.length);
  fetch(`${API_BASE_URL}/events/track`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    keepalive: true,
    body: JSON.stringify({ events: batch }),
  }).catch(() => {/* 静默失败 */});
}

function scheduleFlush() {
  if (timer) return;
  timer = setTimeout(() => {
    timer = null;
    flush();
  }, FLUSH_INTERVAL_MS);
}

function bindPagehideFlush() {
  if (pagehideBound || typeof window === 'undefined') return;
  pagehideBound = true;
  window.addEventListener('pagehide', () => {
    if (queue.length === 0) return;
    const batch = queue.splice(0, queue.length);
    const payload = JSON.stringify({ events: batch });
    const endpoint = `${API_BASE_URL}/events/track`;
    try {
      if (navigator.sendBeacon) {
        const blob = new Blob([payload], { type: 'application/json' });
        navigator.sendBeacon(endpoint, blob);
      } else {
        fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          keepalive: true,
          body: payload,
        }).catch(() => {});
      }
    } catch {
      // 静默失败
    }
  });
}

export function track(
  eventName: string,
  properties?: Record<string, unknown>,
  sessionId?: string,
  userId?: string,
) {
  bindPagehideFlush();
  queue.push({
    event_name: eventName,
    session_id: sessionId,
    user_id: userId,
    properties,
    ts: new Date().toISOString(),
  });
  if (queue.length >= FLUSH_BATCH_SIZE) {
    if (timer) { clearTimeout(timer); timer = null; }
    flush();
  } else {
    scheduleFlush();
  }
}
