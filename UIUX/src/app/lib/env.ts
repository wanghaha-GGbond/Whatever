const rawAppEnv = (import.meta.env.VITE_APP_ENV || import.meta.env.MODE || 'development').toString().toLowerCase();
const rawFallbackFlag = (import.meta.env.VITE_ENABLE_MOCK_FALLBACK || '').toString().trim().toLowerCase();

export const APP_ENV = rawAppEnv;
export const IS_PROD_ENV = rawAppEnv === 'production' || rawAppEnv === 'prod';

export const ENABLE_MOCK_FALLBACK =
  rawFallbackFlag === 'true' ? true :
  rawFallbackFlag === 'false' ? false :
  !IS_PROD_ENV;

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
export const DASHBOARD_ADMIN_TOKEN = (import.meta.env.VITE_DASHBOARD_ADMIN_TOKEN || '').toString().trim();
