/**
 * Shared frontend types mirrored from backend Pydantic models (nm-8gm).
 * Keep field names in snake_case to match API payloads.
 */

// ---- Config ----

export interface AppConfig {
  asset_base_url: string;
  has_openai_key: boolean;
}

// ---- Search requests ----

export interface LexicalSearchRequest {
  must_terms?: string[];
  regexes?: string[];
  path_like?: string | null;
  k?: number;
}

export interface SemanticSearchRequest {
  query: string;
  k?: number;
}

export interface HybridSearchRequest {
  query?: string | null;
  must_terms?: string[];
  regexes?: string[];
  path_like?: string | null;
  k?: number;
  w_semantic?: number;
  w_lexical?: number;
}

// ---- Search results ----

export interface SearchResultMetadata {
  language?: string | null;
  last_updated?: string | null;
  [key: string]: unknown; // allow extra keys
}

export interface BaseSearchResult {
  doc_id: string;
  source_path?: string | null;
  score: number;
  page_uris: string[];
  line_start?: number | null;
  line_end?: number | null;
  why: string[];
  metadata: SearchResultMetadata;
  lex_term_hits?: number;
  lex_regex_hits?: number;
}

export interface HybridSearchResult extends BaseSearchResult {
  sem_score: number;
  lex_score: number;
  rrf_score: number;
}

// ---- Documents & pages ----

export interface DocumentInfo {
  doc_id: string;
  source_path?: string | null;
  language?: string | null;
  last_updated?: string | null;
}

export interface PageRecord {
  doc_id: string;
  page: number;
  uri: string;
  width: number;
  height: number;
  bytes?: number | null;
  sha256?: string | null;
  source_file?: string | null;
}

export interface ChunkInfo {
  chunk_id: string;
  doc_id: string;
  text: string;
  source_path?: string | null;
  line_start?: number | null;
  line_end?: number | null;
}

// ---- Pipeline / cart / state ----

export type PipelineStage = "retrieve" | "assemble" | "render";

export interface CartItem extends HybridSearchResult {
  chunk_id?: string;
  text?: string;
}

export type SearchMode = "semantic" | "lexical" | "hybrid";

export interface SearchState {
  mode: SearchMode;
  query: string;
  must_terms: string[];
  regexes: string[];
  path_like: string | null;
  k: number;
  w_semantic: number;
  w_lexical: number;
  results: HybridSearchResult[];
  selected_result_id: string | null;
  is_searching: boolean;
  error?: string | null;
}

