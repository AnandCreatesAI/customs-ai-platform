import { NextResponse } from 'next/server';

import {
  forwardDjangoJson,
  handleDjangoFailure,
  readAuthCookies,
  rejectUnauthenticated,
} from '@/lib/server/bff';
import { djangoRequest } from '@/lib/server/django-client';
import { isValidConversationId } from '@/lib/server/validation';

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function PATCH(request: Request, context: RouteContext) {
  const stored = await readAuthCookies();
  if (!stored.sessionId) {
    return rejectUnauthenticated();
  }

  const { id } = await context.params;
  if (!isValidConversationId(id)) {
    return NextResponse.json({ detail: 'Invalid conversation id.' }, { status: 400 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: 'Invalid JSON body.' }, { status: 400 });
  }

  try {
    const djangoResponse = await djangoRequest({
      path: `/api/v1/conversations/${id}/`,
      method: 'PATCH',
      cookies: stored,
      body,
    });
    return forwardDjangoJson(
      djangoResponse.status,
      djangoResponse.data,
      djangoResponse.setCookieHeaders,
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
    return NextResponse.json({ detail: 'Invalid conversation id.' }, { status: 400 });
  }

  try {
    const djangoResponse = await djangoRequest({
      path: `/api/v1/conversations/${id}/`,
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

export async function GET(_request: Request, context: RouteContext) {
  const stored = await readAuthCookies();
  if (!stored.sessionId) {
    return rejectUnauthenticated();
  }

  const { id } = await context.params;
  if (!isValidConversationId(id)) {
    return NextResponse.json({ detail: 'Invalid conversation id.' }, { status: 400 });
  }

  try {
    const djangoResponse = await djangoRequest({
      path: `/api/v1/conversations/${id}/`,
      method: 'GET',
      cookies: stored,
    });
    return forwardDjangoJson(
      djangoResponse.status,
      djangoResponse.data,
      djangoResponse.setCookieHeaders,
    );
  } catch (error) {
    return handleDjangoFailure(error);
  }
}
