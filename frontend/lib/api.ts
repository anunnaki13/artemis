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

export async function loginOwner(payload: LoginPayload): Promise<UserSessionResponse> {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    credentials: "include"
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return response.json() as Promise<UserSessionResponse>;
}

export async function getCurrentUser(): Promise<UserSessionResponse> {
  const response = await fetch(`${API_URL}/auth/me`, {
    cache: "no-store",
    credentials: "include"
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return response.json() as Promise<UserSessionResponse>;
}

export async function logoutOwner() {
  await fetch(`${API_URL}/auth/logout`, {
    method: "POST",
    credentials: "include"
  });
}
