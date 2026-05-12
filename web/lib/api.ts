/**
 * Typed client for the Velix FastAPI backend.
 *
 * The base URL is read from NEXT_PUBLIC_API_URL at build time, falling back
 * to the deployed Modal URL so things work out-of-the-box without env-var
 * config.
 */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "https://bhumishdayal--velix-api.modal.run";

// ─────────────────────────────────────────────────────────────────────────
// Response types — mirror the FastAPI Pydantic responses.
// ─────────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  documents: number;
  indexed_pages: number;
  cached_extractions: number;
}

export interface SearchHit {
  score: number;
  source: string;
  source_id: string;
  page_number: number;
  file_path: string;
  title: string;
  snippet?: string;
}

export interface SearchResponse {
  query: string;
  limit: number;
  source_filter: string | null;
  source_id_filter?: string | null;
  hits: SearchHit[];
}

export interface DocumentSummary {
  source: string;
  source_id: string;
  page_count: number;
  sha256: string;
  title: string;
  metadata: Record<string, unknown>;
}

export interface DocumentListResponse {
  total: number;
  offset: number;
  limit: number;
  source_filter: string | null;
  documents: DocumentSummary[];
}

export interface ExtractRequest {
  source: string;
  source_id: string;
  page_number: number;
  schema_name: string;
}

export interface ExtractResponse {
  source: string;
  source_id: string;
  page_number: number;
  schema_name: string;
  cached: boolean;
  extraction: Record<string, unknown>;
}

// ─────────────────────────────────────────────────────────────────────────
// Fetch helpers
// ─────────────────────────────────────────────────────────────────────────

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = await res.json();
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail, `${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

// ─────────────────────────────────────────────────────────────────────────
// Public API
// ─────────────────────────────────────────────────────────────────────────

export const api = {
  health: (signal?: AbortSignal) => request<HealthResponse>("/health", { signal }),

  search: (
    q: string,
    opts: {
      limit?: number;
      source?: string;
      sourceId?: string;
      signal?: AbortSignal;
    } = {},
  ) => {
    const params = new URLSearchParams({ q });
    if (opts.limit) params.set("limit", String(opts.limit));
    if (opts.source) params.set("source", opts.source);
    if (opts.sourceId) params.set("source_id", opts.sourceId);
    return request<SearchResponse>(`/search?${params}`, { signal: opts.signal });
  },

  listDocuments: (
    opts: {
      offset?: number;
      limit?: number;
      source?: string;
      signal?: AbortSignal;
    } = {},
  ) => {
    const params = new URLSearchParams();
    if (opts.offset) params.set("offset", String(opts.offset));
    if (opts.limit) params.set("limit", String(opts.limit));
    if (opts.source) params.set("source", opts.source);
    const qs = params.toString();
    return request<DocumentListResponse>(
      `/documents${qs ? `?${qs}` : ""}`,
      { signal: opts.signal },
    );
  },

  getDocument: (source: string, sourceId: string, signal?: AbortSignal) =>
    request<DocumentSummary>(
      `/documents/${encodeURIComponent(source)}/${encodeURIComponent(sourceId)}`,
      { signal },
    ),

  documentPdfUrl: (source: string, sourceId: string) =>
    `${API_URL}/documents/${encodeURIComponent(source)}/${encodeURIComponent(sourceId)}/pdf`,

  extract: (body: ExtractRequest, refresh = false, signal?: AbortSignal) =>
    request<ExtractResponse>(`/extract${refresh ? "?refresh=true" : ""}`, {
      method: "POST",
      body: JSON.stringify(body),
      signal,
    }),
};

export { ApiError };
