import {
  CHATBOT_PROXY_TIMEOUT_MS,
  DEFAULT_PROXY_TIMEOUT_MS,
} from '@/lib/server/constants';
import {
  buildDjangoCookieHeader,
  getDjangoApiBaseUrl,
  parseSetCookieHeaders,
  type DjangoCookieValues,
} from '@/lib/server/cookies';

const ALLOWED_PATH_PREFIXES = [
  '/api/v1/auth/',
  '/api/v1/chatbot/messages/',
  '/api/v1/chatbot/regenerate/',
  '/api/v1/conversations/',
  '/api/v1/documents/',
] as const;

export class DjangoRequestError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'DjangoRequestError';
  }
}

export class DjangoNetworkError extends DjangoRequestError {
  constructor(message = 'Unable to reach the backend service.') {
    super(message);
    this.name = 'DjangoNetworkError';
  }
}

export class DjangoTimeoutError extends DjangoRequestError {
  constructor(message = 'Backend request timed out.') {
    super(message);
    this.name = 'DjangoTimeoutError';
  }
}

export class DjangoPathNotAllowedError extends DjangoRequestError {
  constructor(path: string) {
    super(`Path not allowed: ${path}`);
    this.name = 'DjangoPathNotAllowedError';
  }
}

export type DjangoResponse<T = unknown> = {
  status: number;
  data: T;
  setCookieHeaders: string[];
};

export function assertAllowedDjangoPath(path: string): void {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  const allowed = ALLOWED_PATH_PREFIXES.some((prefix) => normalized.startsWith(prefix));
  if (!allowed) {
    throw new DjangoPathNotAllowedError(normalized);
  }
}

export function isUnsafeMethod(method: string): boolean {
  return !['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method.toUpperCase());
}

function getSetCookieHeaders(response: Response): string[] {
  if (typeof response.headers.getSetCookie === 'function') {
    return response.headers.getSetCookie();
  }
  const single = response.headers.get('set-cookie');
  return single ? [single] : [];
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return { detail: 'Invalid JSON response from backend.' };
  }
}

export async function djangoRequest<T = unknown>(options: {
  path: string;
  method?: string;
  body?: unknown;
  formData?: FormData;
  query?: Record<string, string | string[] | undefined>;
  cookies?: DjangoCookieValues;
  timeoutMs?: number;
}): Promise<DjangoResponse<T>> {
  const method = (options.method ?? 'GET').toUpperCase();
  assertAllowedDjangoPath(options.path);

  const baseUrl = getDjangoApiBaseUrl().replace(/\/$/, '');
  const url = new URL(`${baseUrl}${options.path}`);
  if (options.query) {
    for (const [key, value] of Object.entries(options.query)) {
      if (value === undefined) {
        continue;
      }
      if (Array.isArray(value)) {
        for (const entry of value) {
          url.searchParams.append(key, entry);
        }
      } else {
        url.searchParams.set(key, value);
      }
    }
  }

  const headers = new Headers({
    Accept: 'application/json',
  });

  const cookieHeader = buildDjangoCookieHeader(
    options.cookies?.sessionId,
    options.cookies?.csrfToken,
  );
  if (cookieHeader) {
    headers.set('Cookie', cookieHeader);
  }

  if (isUnsafeMethod(method) && options.cookies?.csrfToken) {
    headers.set('X-CSRFToken', options.cookies.csrfToken);
  }

  let body: BodyInit | undefined;
  if (options.formData !== undefined) {
    body = options.formData;
  } else if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json');
    body = JSON.stringify(options.body);
  }

  const timeoutMs = options.timeoutMs ?? DEFAULT_PROXY_TIMEOUT_MS;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method,
      headers,
      body,
      signal: controller.signal,
      cache: 'no-store',
    });
    const data = (await parseResponseBody(response)) as T;
    return {
      status: response.status,
      data,
      setCookieHeaders: getSetCookieHeaders(response),
    };
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new DjangoTimeoutError();
    }
    throw new DjangoNetworkError();
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function bootstrapDjangoCsrf(
  existingCookies?: DjangoCookieValues,
): Promise<DjangoResponse<{ csrfToken: string }>> {
  return djangoRequest<{ csrfToken: string }>({
    path: '/api/v1/auth/csrf/',
    method: 'GET',
    cookies: existingCookies,
  });
}

export function mergeCookieValues(
  stored: DjangoCookieValues,
  fromSetCookie: string[],
): DjangoCookieValues {
  const parsed = parseSetCookieHeaders(fromSetCookie);
  return {
    sessionId: parsed.sessionId ?? stored.sessionId,
    csrfToken: parsed.csrfToken ?? stored.csrfToken,
  };
}

export function chatbotTimeoutMs(): number {
  return CHATBOT_PROXY_TIMEOUT_MS;
}
