import {
  forwardDjangoJson,
  handleDjangoFailure,
  readAuthCookies,
  rejectUnauthenticated,
} from '@/lib/server/bff';
import { djangoRequest } from '@/lib/server/django-client';

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(_request: Request, context: RouteContext) {
  const stored = await readAuthCookies();
  if (!stored.sessionId) {
    return rejectUnauthenticated();
  }

  const { id } = await context.params;

  try {
    const djangoResponse = await djangoRequest({
      path: `/api/v1/documents/${id}/`,
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
