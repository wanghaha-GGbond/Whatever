const PRO_KEY = 'pro_unlocked';

export function isPro(): boolean {
  return true; // TODO: 测试期间全员解锁，上线订阅时改回 localStorage 检查
  try {
    return localStorage.getItem(PRO_KEY) === 'true';
  } catch {
    return false;
  }
}

export function setPro(value: boolean): void {
  try {
    localStorage.setItem(PRO_KEY, value ? 'true' : 'false');
  } catch {
    // ignore
  }
}
