export const SESSION_COOKIE_NAME = 'customs.session';
export const CSRF_COOKIE_NAME = 'customs.csrf';

export const DJANGO_SESSION_COOKIE_NAME = 'sessionid';
export const DJANGO_CSRF_COOKIE_NAME = 'csrftoken';

export const DEFAULT_DJANGO_API_BASE_URL = 'http://127.0.0.1:8000';

export const CHATBOT_PROXY_TIMEOUT_MS = 90_000;
export const DEFAULT_PROXY_TIMEOUT_MS = 30_000;

export const ALLOWED_BROWSER_ORIGINS = new Set([
  'http://localhost:3000',
  'http://127.0.0.1:3000',
]);
