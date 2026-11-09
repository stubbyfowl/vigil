async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : `Request failed with status ${res.status}.`);
  }
  return res.json() as Promise<T>;
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body ?? {}),
});

export const get = <T,>(path: string) => request<T>(path);
export const post = <T,>(path: string, body?: unknown) => request<T>(path, json("POST", body));
export const put = <T,>(path: string, body?: unknown) => request<T>(path, json("PUT", body));
