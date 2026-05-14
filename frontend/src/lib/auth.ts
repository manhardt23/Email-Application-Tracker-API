const TOKEN_STORAGE_KEY = "email_tracker_jwt";

type JwtPayload = {
  exp?: number;
  sub?: string;
  role?: string;
};

function decodePayload(token: string): JwtPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) {
      return null;
    }
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const normalized = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    return JSON.parse(window.atob(normalized)) as JwtPayload;
  } catch {
    return null;
  }
}

export function getTokenRole(): string | null {
  const token = getToken();
  if (!token) {
    return null;
  }
  const payload = decodePayload(token);
  return payload?.role ?? null;
}

export function getToken(): string | null {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export function isTokenValid(token: string): boolean {
  const payload = decodePayload(token);
  if (!payload?.exp) {
    return false;
  }
  return payload.exp * 1000 > Date.now();
}

export function getValidToken(): string | null {
  const token = getToken();
  if (!token) {
    return null;
  }
  if (!isTokenValid(token)) {
    clearToken();
    return null;
  }
  return token;
}
