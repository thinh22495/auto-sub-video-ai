const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private buildUrl(path: string, params?: Record<string, string>): string {
    const url = new URL(`${this.baseUrl}${path}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.set(key, value);
      });
    }
    return url.toString();
  }

  async get<T>(path: string, options?: RequestOptions): Promise<T> {
    const { params, ...fetchOptions } = options || {};
    const res = await fetch(this.buildUrl(path, params), {
      method: "GET",
      ...fetchOptions,
    });
    if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
    return res.json();
  }

  async post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    const { params, ...fetchOptions } = options || {};
    const res = await fetch(this.buildUrl(path, params), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
      ...fetchOptions,
    });
    if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
    return res.json();
  }

  async put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    const { params, ...fetchOptions } = options || {};
    const res = await fetch(this.buildUrl(path, params), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
      ...fetchOptions,
    });
    if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
    return res.json();
  }

  async delete<T>(path: string, options?: RequestOptions): Promise<T> {
    const { params, ...fetchOptions } = options || {};
    const res = await fetch(this.buildUrl(path, params), {
      method: "DELETE",
      ...fetchOptions,
    });
    if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
    return res.json();
  }
}

export const api = new ApiClient(API_BASE);
