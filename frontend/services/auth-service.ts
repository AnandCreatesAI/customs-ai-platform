import type { LoginSuccessUser } from '@/services/login-service';

export type AuthUser = LoginSuccessUser;

export type MeResult =
  | { ok: true; user: AuthUser }
  | {
      ok: false;
      status: number;
      message: string;
      unauthenticated: boolean;
    };

export type LogoutResult =
  | { ok: true }
  | { ok: false; status: number; message: string };

function extractDetail(data: unknown, fallback: string): string {
  if (typeof data === 'object' && data !== null && 'detail' in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
  }
  return fallback;
}

export async function fetchMe(): Promise<MeResult> {
  try {
    const response = await fetch('/api/auth/me', {
      method: 'GET',
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
      cache: 'no-store',
    });

    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (response.ok && typeof data === 'object' && data !== null) {
      return { ok: true, user: data as AuthUser };
    }

    if (response.status === 401) {
      return {
        ok: false,
        status: 401,
        message: extractDetail(data, 'Authentication credentials were not provided.'),
        unauthenticated: true,
      };
    }

    return {
      ok: false,
      status: response.status,
      message: extractDetail(data, 'Unable to verify your session. Please try again.'),
      unauthenticated: false,
    };
  } catch {
    return {
      ok: false,
      status: 0,
      message: 'Unable to reach the server. Please try again.',
      unauthenticated: false,
    };
  }
}

export async function submitLogout(): Promise<LogoutResult> {
  try {
    const response = await fetch('/api/auth/logout', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      credentials: 'same-origin',
      body: JSON.stringify({}),
    });

    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (response.ok) {
      return { ok: true };
    }

    return {
      ok: false,
      status: response.status,
      message: extractDetail(data, 'Unable to sign out. Please try again.'),
    };
  } catch {
    return {
      ok: false,
      status: 0,
      message: 'Unable to reach the server. Please try again.',
    };
  }
}
