export type LoginSuccessUser = {
  id: number;
  email: string;
  role: string;
  is_active: boolean;
};

export type LoginResult =
  | { ok: true; user: LoginSuccessUser }
  | { ok: false; status: number; message: string };

function extractErrorMessage(data: unknown): string {
  if (typeof data === 'object' && data !== null && 'detail' in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
  }
  return 'Unable to sign in. Please try again.';
}

export async function submitLogin(
  email: string,
  password: string,
): Promise<LoginResult> {
  try {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      credentials: 'same-origin',
      body: JSON.stringify({ email: email.trim(), password }),
    });

    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (response.ok && typeof data === 'object' && data !== null) {
      return { ok: true, user: data as LoginSuccessUser };
    }

    return {
      ok: false,
      status: response.status,
      message: extractErrorMessage(data),
    };
  } catch {
    return {
      ok: false,
      status: 0,
      message: 'Unable to reach the server. Please try again.',
    };
  }
}
