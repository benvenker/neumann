import {
  AppConfig,
  ChunkInfo,
  DocumentInfo,
  BaseSearchResult,
  HybridSearchResult,
  HybridSearchRequest,
  LexicalSearchRequest,
  PageRecord,
  SearchResultMetadata,
  SemanticSearchRequest,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8001";
const API_PREFIX = "/api/v1";

/**
 * Typed error raised for non-2xx API responses.
 */
export class ApiError extends Error {
  status: number;
  detail: string | Record<string, unknown> | null;
  endpoint: string;

  constructor(status: number, endpoint: string, detail: unknown) {
    const friendly =
      typeof detail === "string"
        ? detail
        : detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : "Request failed";
    super(`API ${status}: ${friendly}`);
    this.status = status;
    this.endpoint = endpoint;
    this.detail =
      typeof detail === "string" || typeof detail === "object" ? (detail as any) : null;
  }
}

type JsonValue = Record<string, unknown> | Array<unknown> | string | number | boolean | null;

const jsonHeaders = {
  "Content-Type": "application/json",
  Accept: "application/json",
};

function buildUrl(endpoint: string): string {
  // Allow callers to pass with or without leading slash; always prefix /api/v1.
  const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  return new URL(`${API_PREFIX}${path}`, API_BASE).toString();
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit & { body?: JsonValue } = {},
): Promise<T> {
  const url = buildUrl(endpoint);
  const { body, headers, ...rest } = options;

  const response = await fetch(url, {
    headers: { ...jsonHeaders, ...(headers || {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    ...rest,
  });

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const parsed = isJson ? await response.json().catch(() => null) : await response.text();

  if (!response.ok) {
    throw new ApiError(response.status, endpoint, parsed);
  }

  return (parsed as T) ?? ({} as T);
}

function ensureK(value: number | undefined, field: "k" = "k"): void {
  if (value !== undefined && value < 1) {
    throw new ApiError(400, field, `${field} must be >= 1`);
  }
}

function validateLexicalInput(payload: LexicalSearchRequest): void {
  const hasFilters = Boolean(
    (payload.must_terms && payload.must_terms.length) ||
      (payload.regexes && payload.regexes.length) ||
      payload.path_like,
  );
  if (!hasFilters) {
    throw new ApiError(400, "/search/lexical", "Provide at least one of must_terms, regexes, or path_like");
  }
  ensureK(payload.k);
}

function validateSemanticInput(payload: SemanticSearchRequest): void {
  const query = (payload.query || "").trim();
  if (!query) {
    throw new ApiError(400, "/search/semantic", "query must be non-empty");
  }
  ensureK(payload.k);
}

function validateHybridInput(payload: HybridSearchRequest): void {
  const hasSem = Boolean((payload.query || "").trim());
  const hasLex = Boolean(
    (payload.must_terms && payload.must_terms.length) ||
      (payload.regexes && payload.regexes.length) ||
      payload.path_like,
  );

  if (!hasSem && !hasLex) {
    throw new ApiError(400, "/search/hybrid", "At least one of query or lexical filters must be provided");
  }

  if (payload.w_semantic !== undefined && (payload.w_semantic < 0 || payload.w_semantic > 1)) {
    throw new ApiError(400, "w_semantic", "w_semantic must be between 0 and 1");
  }
  if (payload.w_lexical !== undefined && (payload.w_lexical < 0 || payload.w_lexical > 1)) {
    throw new ApiError(400, "w_lexical", "w_lexical must be between 0 and 1");
  }
  const wSem = payload.w_semantic ?? 0.6;
  const wLex = payload.w_lexical ?? 0.4;
  if (wSem + wLex <= 0) {
    throw new ApiError(400, "weights", "w_semantic + w_lexical must be > 0");
  }
  ensureK(payload.k);
}

/**
 * Placeholder until nm-mba implements shared asset URL rebasing.
 * Returns absolute URLs unchanged; otherwise prefixes assetBasePath.
 */
export function resolveAssetUrl(
  uri: string,
  apiBase: string = API_BASE,
  assetBasePath: string = `${API_PREFIX}/assets`,
): string {
  if (!uri) return uri;
  if (/^https?:\/\//i.test(uri)) return uri;
  const base = apiBase.endsWith("/") ? apiBase.slice(0, -1) : apiBase;
  const path = uri.startsWith("/") ? uri : `/${uri}`;
  return `${base}${assetBasePath}${path}`;
}

export const apiClient = {
  async fetchConfig(): Promise<AppConfig> {
    return apiRequest<AppConfig>("/config");
  },

  async searchLexical(payload: LexicalSearchRequest): Promise<BaseSearchResult[]> {
    validateLexicalInput(payload);
    return apiRequest<BaseSearchResult[]>("/search/lexical", {
      method: "POST",
      body: payload,
    });
  },

  async searchSemantic(payload: SemanticSearchRequest): Promise<BaseSearchResult[]> {
    validateSemanticInput(payload);
    return apiRequest<BaseSearchResult[]>("/search/semantic", {
      method: "POST",
      body: payload,
    });
  },

  async searchHybrid(payload: HybridSearchRequest): Promise<HybridSearchResult[]> {
    validateHybridInput(payload);
    return apiRequest<HybridSearchResult[]>("/search/hybrid", {
      method: "POST",
      body: payload,
    });
  },

  async fetchDocuments(): Promise<DocumentInfo[]> {
    return apiRequest<DocumentInfo[]>("/docs");
  },

  async fetchDocumentPages(docId: string): Promise<PageRecord[]> {
    const encoded = encodeURIComponent(docId);
    return apiRequest<PageRecord[]>(`/docs/${encoded}/pages`);
  },

  async fetchDocumentChunks(docId: string): Promise<ChunkInfo[]> {
    const encoded = encodeURIComponent(docId);
    return apiRequest<ChunkInfo[]>(`/docs/${encoded}/chunks`);
  },
};

export type SearchResult = HybridSearchResult & { metadata: SearchResultMetadata };
