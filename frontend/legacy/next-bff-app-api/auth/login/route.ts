import { NextResponse } from 'next/server';

import {
  ensureCsrfForUnsafeRequest,
  forwardDjangoJson,
  handleDjangoFailure,
  readAuthCookies,
  requireStateChangingOrigin,
} from '@/lib/server/bff';
import { djangoRequest } from '@/lib/server/django-client';

type LoginBody = {
  email?: string;
  password?: string;
};

export async function POST(request: Request) {
  const originFailure = requireStateChangingOrigin(request);
  if (originFailure) {
    return originFailure;
  }
  let body: LoginBody;
  try {
    body = (await request.json()) as LoginBody;
  } catch {
    return NextResponse.json({ detail: 'Invalid JSON body.' }, { status: 400 });
  }

  try {
    const stored = await readAuthCookies();
    const { cookies, setCookieHeaders: csrfSetCookies } = await ensureCsrfForUnsafeRequest(stored);

    const djangoResponse = await djangoRequest({
      path: '/api/v1/auth/login/',
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
