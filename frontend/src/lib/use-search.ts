"use client";

import { useCallback, useMemo, useState } from "react";

import { apiClient, ApiError } from "./api-client";
import {
  HybridSearchRequest,
  HybridSearchResult,
  LexicalSearchRequest,
  SearchMode,
  SemanticSearchRequest,
} from "./types";
import { useConfigContext } from "@/app/app-providers";

export interface UseSearchState {
  mode: SearchMode;
  query: string;
  mustTerms: string[];
  regexes: string[];
  pathLike: string | null;
  k: number;
  wSemantic: number;
  wLexical: number;
  results: HybridSearchResult[];
  isSearching: boolean;
  error: string | null;
  setQuery: (v: string) => void;
  setMustTerms: (v: string[]) => void;
  setRegexes: (v: string[]) => void;
  setPathLike: (v: string | null) => void;
  setK: (v: number) => void;
  setWeights: (wSemantic: number, wLexical: number) => void;
  executeSearch: () => Promise<void>;
  clearResults: () => void;
}

const DEFAULT_K = 12;
const DEFAULT_W_SEM = 0.6;
const DEFAULT_W_LEX = 0.4;

function deriveMode(
  hasOpenAiKey: boolean,
  query: string,
  hasLex: boolean,
): SearchMode {
  const hasSem = Boolean(query.trim());
  if (!hasOpenAiKey && hasSem && hasLex) return "lexical"; // degrade: no semantic channel available
  if (!hasOpenAiKey && hasSem) return "lexical";
  if (hasSem && hasLex) return "hybrid";
  if (hasSem) return "semantic";
  return "lexical";
}

export function useSearch(): UseSearchState {
  const { config } = useConfigContext();
  const hasOpenAiKey = config?.has_openai_key ?? false;

  const [query, setQuery] = useState<string>("");
  const [mustTerms, setMustTerms] = useState<string[]>([]);
  const [regexes, setRegexes] = useState<string[]>([]);
  const [pathLike, setPathLike] = useState<string | null>(null);
  const [k, setK] = useState<number>(DEFAULT_K);
  const [wSemantic, setWSemantic] = useState<number>(DEFAULT_W_SEM);
  const [wLexical, setWLexical] = useState<number>(DEFAULT_W_LEX);
  const [results, setResults] = useState<HybridSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const hasLex = useMemo(
    () => Boolean(mustTerms.length || regexes.length || pathLike),
    [mustTerms, regexes, pathLike],
  );

  const mode = useMemo(() => deriveMode(hasOpenAiKey, query, hasLex), [hasOpenAiKey, query, hasLex]);

  const setWeights = useCallback(
    (wSem: number, wLex: number) => {
      setWSemantic(wSem);
      setWLexical(wLex);
    },
    [],
  );

  const clearResults = useCallback(() => {
    setResults([]);
    setError(null);
  }, []);

  const executeSearch = useCallback(async () => {
    setIsSearching(true);
    setError(null);

    const trimmedQuery = query.trim();
    const hasSem = Boolean(trimmedQuery);
    const hasLexInner = Boolean(mustTerms.length || regexes.length || pathLike);

    // Determine effective mode based on availability and inputs
    const effectiveMode = deriveMode(hasOpenAiKey, trimmedQuery, hasLexInner);

    try {
      if (!hasOpenAiKey && hasSem && !hasLexInner) {
        throw new ApiError(
          400,
          "validation",
          "Semantic search is unavailable without OPENAI_API_KEY. Add must_terms/regex/path filters or configure a key.",
        );
      }

      if (!hasSem && !hasLexInner) {
        throw new ApiError(400, "validation", "Provide a query or at least one lexical filter");
      }

      if (effectiveMode === "semantic") {
        const payload: SemanticSearchRequest = { query: trimmedQuery, k };
        const res = await apiClient.searchSemantic(payload);
        setResults(res as HybridSearchResult[]);
        return;
      }

      if (effectiveMode === "lexical") {
        const payload: LexicalSearchRequest = {
          must_terms: mustTerms,
          regexes,
          path_like: pathLike,
          k,
        };
        const res = await apiClient.searchLexical(payload);
        setResults(res as HybridSearchResult[]);
        return;
      }

      const payload: HybridSearchRequest = {
        query: trimmedQuery,
        must_terms: mustTerms,
        regexes,
        path_like: pathLike,
        k,
        w_semantic: wSemantic,
        w_lexical: wLexical,
      };
      const res = await apiClient.searchHybrid(payload);
      setResults(res);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Search failed";
      setError(msg);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [hasOpenAiKey, k, mustTerms, pathLike, query, regexes, wLexical, wSemantic]);

  return {
    mode,
    query,
    mustTerms,
    regexes,
    pathLike,
    k,
    wSemantic,
    wLexical,
    results,
    isSearching,
    error,
    setQuery,
    setMustTerms,
    setRegexes,
    setPathLike,
    setK,
    setWeights,
    executeSearch,
    clearResults,
  };
}
