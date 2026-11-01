import {
  forwardDjangoJson,
  handleDjangoFailure,
  readAuthCookies,
  rejectUnauthenticated,
} from '@/lib/server/bff';
import { djangoRequest } from '@/lib/server/django-client';

export async function GET() {
  const stored = await readAuthCookies();
  if (!stored.sessionId) {
    return rejectUnauthenticated();
  }

  try {
    const djangoResponse = await djangoRequest({
      path: '/api/v1/auth/me/',
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
