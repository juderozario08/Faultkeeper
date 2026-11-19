export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, body: unknown) {
    const detail = typeof body === "object" && body && "detail" in body ? String(body.detail) : "";
    super(detail || `Request failed with status ${status}`);
    this.status = status;
    this.body = body;
  }
}

function csrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export async function api<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, headers, ...rest } = init;
  const method = (rest.method ?? "GET").toUpperCase();
  const response = await fetch(path.startsWith("/") ? path : `/api/0/${path}`, {
    credentials: "same-origin",
    ...rest,
    method,
    headers: {
      Accept: "application/json",
      ...(json !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(method !== "GET" ? { "X-CSRFToken": csrfToken() } : {}),
      ...headers,
    },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
  if (response.status === 204) return undefined as T;
  const body = response.headers.get("content-type")?.includes("json") ? await response.json() : await response.text();
  if (!response.ok) throw new ApiError(response.status, body);
  return body as T;
}

/** Makes sure the CSRF cookie exists before the first unsafe request. */
export function ensureCsrf(): Promise<unknown> {
  return csrfToken() ? Promise.resolve() : api("auth/csrf/");
}
