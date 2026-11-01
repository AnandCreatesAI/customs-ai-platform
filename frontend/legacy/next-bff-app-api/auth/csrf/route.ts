import {
  forwardDjangoJson,
  handleDjangoFailure,
  readAuthCookies,
} from '@/lib/server/bff';
import { djangoRequest } from '@/lib/server/django-client';

export async function GET() {
  try {
    const stored = await readAuthCookies();
    const djangoResponse = await djangoRequest<{ csrfToken: string }>({
      path: '/api/v1/auth/csrf/',
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
