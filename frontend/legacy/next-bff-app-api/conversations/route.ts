import {
  forwardDjangoJson,
  handleDjangoFailure,
  readAuthCookies,
  rejectUnauthenticated,
} from '@/lib/server/bff';
import { djangoRequest } from '@/lib/server/django-client';

export async function GET(request: Request) {
  const stored = await readAuthCookies();
  if (!stored.sessionId) {
    return rejectUnauthenticated();
  }

  const incoming = new URL(request.url);
  const query: Record<string, string> = {};
  for (const key of ['page', 'page_size']) {
    const value = incoming.searchParams.get(key);
    if (value !== null) {
      query[key] = value;
    }
  }

  try {
    const djangoResponse = await djangoRequest({
      path: '/api/v1/conversations/',
      method: 'GET',
      cookies: stored,
      query,
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
