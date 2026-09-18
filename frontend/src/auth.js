const TOKEN_KEY = "metaconnect_token";
const USERNAME_KEY = "metaconnect_username";
const USER_INFO_KEY = "metaconnect_user_info";
export const AUTH_CHANGE_EVENT = "metaconnect-auth-change";

const KEYCLOAK_URL =
  import.meta.env.VITE_KEYCLOAK_URL || "http://localhost:8082";
const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM || "metaconnect";
const KEYCLOAK_CLIENT_ID =
  import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "metaconnect-api";

function notifyAuthChange() {
  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
}

function readTokenClaims(token) {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return {};
  }
}

export async function login(username, password) {
  const res = await fetch(
    `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`,
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: KEYCLOAK_CLIENT_ID,
        grant_type: "password",
        username,
        password,
      }),
    },
  );

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const errorCode = data.error || `http_${res.status}`;
    const errorMessage = data.error_description || "Authentication failed";
    console.warn("Keycloak login failed", {
      status: res.status,
      error: errorCode,
      description: errorMessage,
      username,
    });
    throw new Error(`${errorMessage} (${errorCode}, HTTP ${res.status})`);
  }

  console.info("Keycloak login succeeded", { username });
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem(USERNAME_KEY, username);
  const claims = readTokenClaims(data.access_token);
  localStorage.setItem(
    USER_INFO_KEY,
    JSON.stringify({
      username: claims.preferred_username || username,
      name:
        claims.name ||
        [claims.given_name, claims.family_name].filter(Boolean).join(" ") ||
        claims.preferred_username ||
        username,
      email: claims.email || "",
    }),
  );
  notifyAuthChange();
  return data.access_token;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USERNAME_KEY);
  localStorage.removeItem(USER_INFO_KEY);
  notifyAuthChange();
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getCurrentUsername() {
  return localStorage.getItem(USERNAME_KEY) || "unknown";
}

export function getCurrentUser() {
  try {
    const stored = JSON.parse(localStorage.getItem(USER_INFO_KEY) || "null");
    if (stored) return stored;
    const claims = readTokenClaims(getToken() || "");
    const username = claims.preferred_username || getCurrentUsername();
    return {
      username,
      name:
        claims.name ||
        [claims.given_name, claims.family_name].filter(Boolean).join(" ") ||
        username,
      email: claims.email || "",
    };
  } catch {
    return {
      username: getCurrentUsername(),
      name: getCurrentUsername(),
      email: "",
    };
  }
}

export function isAuthenticated() {
  return Boolean(getToken());
}
