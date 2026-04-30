const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

type RegisterPayload = {
  email: string;
  password: string;
};

type LoginPayload = RegisterPayload & {
  totp_code: string;
};

export type RegisterResponse = {
  user_id: string;
  totp_secret: string;
  provisioning_uri: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type UserSessionResponse = {
  user_id: string;
  email: string;
  role: string;
};

async function parseApiError(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail)) {
      return payload.detail.map((item) => item?.msg ?? "validation error").join("; ");
    }
  } catch {
    // Fall through to a generic status message.
  }
  return `request failed: ${response.status}`;
}

export async function getDashboardSummary() {
  const response = await fetch(`${API_URL}/dashboard/summary`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("failed to load dashboard summary");
  }
  return response.json();
}

export async function registerOwner(payload: RegisterPayload): Promise<RegisterResponse> {
  const response = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return response.json() as Promise<RegisterResponse>;
}

export async function loginOwner(payload: LoginPayload): Promise<TokenResponse> {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return response.json() as Promise<TokenResponse>;
}

export function storeAccessToken(token: string) {
  sessionStorage.setItem("aiq_access_token", token);
  document.cookie = "aiq_session=1; path=/; max-age=900; samesite=lax";
}

export function getStoredAccessToken() {
  return sessionStorage.getItem("aiq_access_token");
}

export function clearAccessToken() {
  sessionStorage.removeItem("aiq_access_token");
  document.cookie = "aiq_session=; path=/; max-age=0; samesite=lax";
}

export async function getCurrentUser(token: string): Promise<UserSessionResponse> {
  const response = await fetch(`${API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return response.json() as Promise<UserSessionResponse>;
}

export async function logoutOwner(token: string) {
  await fetch(`${API_URL}/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` }
  });
  clearAccessToken();
}
