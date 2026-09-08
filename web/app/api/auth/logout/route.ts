import { cookies } from "next/headers";
import { backendUrl, getSessionToken, isBackendConfigured, SESSION_COOKIE_NAME } from "@/lib/bff";

export async function POST() {
  const token = await getSessionToken();

  if (token && isBackendConfigured()) {
    await fetch(backendUrl("/api/v1/auth/logout"), {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    }).catch(() => {
      // Best-effort revoke — the cookie is cleared below regardless.
    });
  }

  const store = await cookies();
  store.delete(SESSION_COOKIE_NAME);
  return Response.json({ ok: true });
}
