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
import { isValidConversationId } from '@/lib/server/validation';

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function PUT(request: Request, context: RouteContext) {
  const originFailure = requireStateChangingOrigin(request);
  if (originFailure) {
    return originFailure;
  }

  const stored = await readAuthCookies();
  if (!stored.sessionId) {
    return rejectUnauthenticated();
  }

  const { id } = await context.params;
  if (!isValidConversationId(id)) {
    return NextResponse.json({ detail: 'Invalid message id.' }, { status: 400 });
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
      path: `/api/v1/conversations/messages/${id}/feedback/`,
      method: 'PUT',
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

export async function DELETE(_request: Request, context: RouteContext) {
  const stored = await readAuthCookies();
  if (!stored.sessionId) {
    return rejectUnauthenticated();
  }

  const { id } = await context.params;
  if (!isValidConversationId(id)) {
    return NextResponse.json({ detail: 'Invalid message id.' }, { status: 400 });
  }

  try {
    const djangoResponse = await djangoRequest({
      path: `/api/v1/conversations/messages/${id}/feedback/`,
      method: 'DELETE',
      cookies: stored,
    });
    if (djangoResponse.status === 204) {
      return new NextResponse(null, { status: 204 });
    }
    return forwardDjangoJson(
      djangoResponse.status,
      djangoResponse.data,
      djangoResponse.setCookieHeaders,
    );
  } catch (error) {
    return handleDjangoFailure(error);
  }
}
