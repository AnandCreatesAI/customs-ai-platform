const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

let cachedCsrfToken: string | null = null;

export function clearCsrfTokenCache(): void {
  cachedCsrfToken = null;
}

export async function ensureCsrfToken(): Promise<string> {
  if (cachedCsrfToken) {
    return cachedCsrfToken;
  }

  const response = await fetch('/api/auth/csrf', {
    method: 'GET',
    headers: { Accept: 'application/json' },
    credentials: 'same-origin',
    cache: 'no-store',
  });

  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (
    response.ok &&
    typeof data === 'object' &&
    data !== null &&
    typeof (data as { csrfToken?: unknown }).csrfToken === 'string'
  ) {
    cachedCsrfToken = (data as { csrfToken: string }).csrfToken;
    return cachedCsrfToken;
  }

  throw new Error('Unable to obtain CSRF token.');
}

export type ApiFetchOptions = RequestInit & {
  timeoutMs?: number;
};

export async function apiFetch(input: string, init: ApiFetchOptions = {}): Promise<Response> {
  const method = (init.method ?? 'GET').toUpperCase();
  const headers = new Headers(init.headers);
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  if (UNSAFE_METHODS.has(method)) {
    const token = await ensureCsrfToken();
    headers.set('X-CSRFToken', token);
  }

  const { timeoutMs, ...fetchInit } = init;
  let signal = fetchInit.signal;
  let timeoutId: ReturnType<typeof setTimeout> | undefined;

  if (timeoutMs !== undefined && timeoutMs > 0) {
    const controller = new AbortController();
    timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    if (signal) {
      signal.addEventListener('abort', () => controller.abort(), { once: true });
    }
    signal = controller.signal;
  }

  try {
    const response = await fetch(input, {
      ...fetchInit,
      method,
      headers,
      credentials: 'same-origin',
      signal,
    });

    if (response.status === 403 && UNSAFE_METHODS.has(method)) {
      clearCsrfTokenCache();
    }

    return response;
  } finally {
    if (timeoutId !== undefined) {
      clearTimeout(timeoutId);
    }
  }
}

/** Legacy BFF-aligned chatbot proxy timeout (90 seconds). */
export const CHATBOT_API_TIMEOUT_MS = 90_000;
