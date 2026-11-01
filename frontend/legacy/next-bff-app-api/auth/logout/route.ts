import {
  handleDjangoFailure,
  logoutViaDjango,
  readAuthCookies,
  rejectUnauthenticated,
  requireStateChangingOrigin,
} from '@/lib/server/bff';

export async function POST(request: Request) {
  const originFailure = requireStateChangingOrigin(request);
  if (originFailure) {
    return originFailure;
  }

  const stored = await readAuthCookies();
  if (!stored.sessionId) {
    return rejectUnauthenticated();
  }

  try {
    const { response } = await logoutViaDjango(stored);
    return response;
  } catch (error) {
    return handleDjangoFailure(error);
  }
}
