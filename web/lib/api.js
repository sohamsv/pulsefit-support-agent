export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

/** Small fetch helper. Throws an Error with .status and .retryAfter (seconds) on failure. */
export async function api(path, { method = "GET", body, token } = {}) {
  let res;
  try {
    res = await fetch(`${API}${path}`, {
      method,
      headers: {
        ...(body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw Object.assign(new Error("Can't reach the PulseFit server. Please try again."), { status: 0 });
  }
  let data = {};
  try { data = await res.json(); } catch {}
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : (Array.isArray(data.detail) ? "Please check the form and try again." : "Something went wrong.");
    throw Object.assign(new Error(detail), {
      status: res.status,
      retryAfter: Number(data.retry_after || res.headers.get("Retry-After") || 0),
    });
  }
  return data;
}

export const store = {
  get(k) { try { return sessionStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { sessionStorage.setItem(k, v); } catch {} },
  del(k) { try { sessionStorage.removeItem(k); } catch {} },
};
