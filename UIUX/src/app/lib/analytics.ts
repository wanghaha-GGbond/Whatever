/**
 * 轻量级埋点客户端。
 * 事件先入本地队列，每 3 秒或队列满 10 条时批量上报。
 * 上报失败静默忽略，不影响用户体验。
 */

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

function flush() {
  if (queue.length === 0) return;
  const batch = queue.splice(0, queue.length);
  fetch('/api/v1/events/track', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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

export function track(
  eventName: string,
  properties?: Record<string, unknown>,
  sessionId?: string,
  userId?: string,
) {
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
