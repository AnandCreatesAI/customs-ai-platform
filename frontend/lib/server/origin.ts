import { ALLOWED_BROWSER_ORIGINS } from '@/lib/server/constants';

/**
 * Validates browser Origin (or Referer fallback) for state-changing BFF requests.
 */
export function validateBrowserOrigin(request: Request): boolean {
  const origin = request.headers.get('origin');
  if (origin) {
    return ALLOWED_BROWSER_ORIGINS.has(origin);
  }

  const referer = request.headers.get('referer');
  if (!referer) {
    return false;
  }

  try {
    const refererOrigin = new URL(referer).origin;
    return ALLOWED_BROWSER_ORIGINS.has(refererOrigin);
  } catch {
    return false;
  }
}
