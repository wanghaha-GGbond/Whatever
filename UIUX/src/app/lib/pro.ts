const PRO_KEY = 'pro_unlocked';

export function isPro(): boolean {
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
