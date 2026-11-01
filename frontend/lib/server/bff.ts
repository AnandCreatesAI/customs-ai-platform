import { NextResponse } from 'next/server';

import {
  applyDjangoCookiesToResponse,
  clearAuthCookies,
  readStoredDjangoCookies,
} from '@/lib/server/cookies';
import {
  bootstrapDjangoCsrf,
  djangoRequest,
  DjangoNetworkError,
  DjangoTimeoutError,
  mergeCookieValues,
} from '@/lib/server/django-client';
import { validateBrowserOrigin } from '@/lib/server/origin';

export function jsonError(detail: string, status: number): NextResponse {
  return NextResponse.json({ detail }, { status });
}

export function rejectInvalidOrigin(): NextResponse {
  return jsonError('Origin not allowed.', 403);
}

export function rejectUnauthenticated(): NextResponse {
  return jsonError('Authentication credentials were not provided.', 401);
}

export function handleDjangoFailure(error: unknown): NextResponse {
  if (error instanceof DjangoTimeoutError) {
    return jsonError(error.message, 504);
  }
  if (error instanceof DjangoNetworkError) {
    return jsonError(error.message, 503);
  }
  return jsonError('Unexpected BFF error.', 500);
}

export function forwardDjangoJson<T>(
  status: number,
  data: T,
  setCookieHeaders: string[] = [],
): NextResponse {
  const response = NextResponse.json(data, { status });
  applyDjangoCookiesToResponse(response, setCookieHeaders);
  return response;
}

export async function readAuthCookies() {
  const { cookies } = await import('next/headers');
  const cookieStore = await cookies();
  return readStoredDjangoCookies(cookieStore);
}

export async function ensureCsrfForUnsafeRequest(
  stored: { sessionId?: string; csrfToken?: string },
): Promise<{ cookies: { sessionId?: string; csrfToken?: string }; setCookieHeaders: string[] }> {
  if (stored.csrfToken) {
    return { cookies: stored, setCookieHeaders: [] };
  }
  const csrfResponse = await bootstrapDjangoCsrf(stored);
  const cookies = mergeCookieValues(stored, csrfResponse.setCookieHeaders);
  if (!cookies.csrfToken && typeof csrfResponse.data === 'object' && csrfResponse.data !== null) {
    const token = (csrfResponse.data as { csrfToken?: string }).csrfToken;
    if (token) {
      cookies.csrfToken = token;
    }
  }
  return { cookies, setCookieHeaders: csrfResponse.setCookieHeaders };
}

export function requireStateChangingOrigin(request: Request): NextResponse | null {
  if (!validateBrowserOrigin(request)) {
    return rejectInvalidOrigin();
  }
  return null;
}

export async function logoutViaDjango(stored: {
  sessionId?: string;
  csrfToken?: string;
}): Promise<{ response: NextResponse; djangoStatus: number }> {
  const { cookies, setCookieHeaders: csrfSetCookies } = await ensureCsrfForUnsafeRequest(stored);
  const djangoResponse = await djangoRequest({
    path: '/api/v1/auth/logout/',
    method: 'POST',
    body: {},
    cookies,
  });

  const response = NextResponse.json(djangoResponse.data, { status: djangoResponse.status });
  applyDjangoCookiesToResponse(response, [...csrfSetCookies, ...djangoResponse.setCookieHeaders]);
  if (djangoResponse.status >= 200 && djangoResponse.status < 300) {
    clearAuthCookies(response);
  }
  return { response, djangoStatus: djangoResponse.status };
}
