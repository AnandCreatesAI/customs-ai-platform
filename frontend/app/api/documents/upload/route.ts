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

  let incoming: FormData;
  try {
    incoming = await request.formData();
  } catch {
    return NextResponse.json({ detail: 'Invalid multipart body.' }, { status: 400 });
  }

  const forward = new FormData();
  for (const [key, value] of incoming.entries()) {
    if (value instanceof File) {
      forward.append(key, value, value.name);
    } else {
      forward.append(key, value);
    }
  }

  try {
    const { cookies, setCookieHeaders: csrfSetCookies } = await ensureCsrfForUnsafeRequest(stored);
    const djangoResponse = await djangoRequest({
      path: '/api/v1/documents/upload/',
      method: 'POST',
      formData: forward,
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
