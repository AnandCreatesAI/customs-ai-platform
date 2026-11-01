import {
  CSRF_COOKIE_NAME,
  DJANGO_CSRF_COOKIE_NAME,
  DJANGO_SESSION_COOKIE_NAME,
  SESSION_COOKIE_NAME,
} from '@/lib/server/constants';

export function getDjangoApiBaseUrl(): string {
  return process.env.DJANGO_API_BASE_URL ?? 'http://127.0.0.1:8000';
}

export function isProduction(): boolean {
  return process.env.NODE_ENV === 'production';
}

export type BffCookieOptions = {
  httpOnly?: boolean;
  secure?: boolean;
  sameSite?: 'lax' | 'strict' | 'none';
  path?: string;
  maxAge?: number;
};

export function buildSessionCookieOptions(maxAge?: number): BffCookieOptions {
  return {
    httpOnly: true,
    secure: isProduction(),
    sameSite: 'lax',
    path: '/',
    ...(maxAge !== undefined ? { maxAge } : { maxAge: 60 * 60 * 24 * 14 }),
  };
}

export function buildCsrfCookieOptions(maxAge?: number): BffCookieOptions {
  return buildSessionCookieOptions(maxAge);
}

export type DjangoCookieValues = {
  sessionId?: string;
  csrfToken?: string;
};

export function parseSetCookieHeaders(setCookieHeaders: string[]): DjangoCookieValues {
  const values: DjangoCookieValues = {};

  for (const header of setCookieHeaders) {
    const [pair] = header.split(';');
    const separatorIndex = pair.indexOf('=');
    if (separatorIndex === -1) {
      continue;
    }
    const name = pair.slice(0, separatorIndex).trim();
    const value = pair.slice(separatorIndex + 1).trim();
    if (name === DJANGO_SESSION_COOKIE_NAME) {
      values.sessionId = value;
    }
    if (name === DJANGO_CSRF_COOKIE_NAME) {
      values.csrfToken = value;
    }
  }

  return values;
}

export function buildDjangoCookieHeader(
  sessionId?: string,
  csrfToken?: string,
): string | undefined {
  const parts: string[] = [];
  if (sessionId) {
    parts.push(`${DJANGO_SESSION_COOKIE_NAME}=${sessionId}`);
  }
  if (csrfToken) {
    parts.push(`${DJANGO_CSRF_COOKIE_NAME}=${csrfToken}`);
  }
  return parts.length > 0 ? parts.join('; ') : undefined;
}

export function readStoredDjangoCookies(cookieStore: {
  get: (name: string) => { value: string } | undefined;
}): DjangoCookieValues {
  return {
    sessionId: cookieStore.get(SESSION_COOKIE_NAME)?.value,
    csrfToken: cookieStore.get(CSRF_COOKIE_NAME)?.value,
  };
}

export function applyDjangoCookiesToResponse(
  response: { cookies: { set: (name: string, value: string, options?: BffCookieOptions) => void } },
  setCookieHeaders: string[],
): DjangoCookieValues {
  const parsed = parseSetCookieHeaders(setCookieHeaders);

  if (parsed.sessionId) {
    response.cookies.set(SESSION_COOKIE_NAME, parsed.sessionId, buildSessionCookieOptions());
  }
  if (parsed.csrfToken) {
    response.cookies.set(CSRF_COOKIE_NAME, parsed.csrfToken, buildCsrfCookieOptions());
  }

  return parsed;
}

export function clearAuthCookies(response: {
  cookies: { set: (name: string, value: string, options?: BffCookieOptions) => void };
}): void {
  const expired = { ...buildSessionCookieOptions(0), maxAge: 0 };
  response.cookies.set(SESSION_COOKIE_NAME, '', expired);
  response.cookies.set(CSRF_COOKIE_NAME, '', expired);
}

export { CSRF_COOKIE_NAME, SESSION_COOKIE_NAME };
