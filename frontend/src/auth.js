const TOKEN_KEY = "metaconnect_token";

const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL || "http://localhost:8082";
const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM || "metaconnect";
const KEYCLOAK_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "metaconnect-api";

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
    }
  );

  if (!res.ok) {
    throw new Error("Invalid username or password");
  }

  const data = await res.json();
  localStorage.setItem(TOKEN_KEY, data.access_token);
  return data.access_token;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function isAuthenticated() {
  return Boolean(getToken());
}