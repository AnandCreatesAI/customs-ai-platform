import { NextResponse } from 'next/server';

import {
  ensureCsrfForUnsafeRequest,
  forwardDjangoJson,
  handleDjangoFailure,
  readAuthCookies,
  rejectUnauthenticated,
  requireStateChangingOrigin,
} from '@/lib/server/bff';
import { djangoRequest } from '@/lib/server/django-client';

export async function POST(request: Request) {
  const originFailure = requireStateChangingOrigin(request);
  if (originFailure) {
    return originFailure;
  }

  const stored = await readAuthCookies();
  if (!stored.sessionId) {
    return rejectUnauthenticated();
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: 'Invalid JSON body.' }, { status: 400 });
  }

  try {
    const { cookies, setCookieHeaders: csrfSetCookies } = await ensureCsrfForUnsafeRequest(stored);
    const djangoResponse = await djangoRequest({
      path: '/api/v1/documents/json/',
      method: 'POST',
      body,
      cookies,
    });
    return forwardDjangoJson(
      djangoResponse.status,
      djangoResponse.data,
      [...csrfSetCookies, ...djangoResponse.setCookieHeaders],
    );
  } catch (error) {
    return handleDjangoFailure(error);
  }
}
