"use client";

import { useCallback, useEffect, useState } from "react";

import { apiClient } from "./api-client";
import { AppConfig } from "./types";

export interface UseConfigState {
  config: AppConfig | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Fetches AppConfig on mount and provides config/loading/error state.
 */
export function useConfig(): UseConfigState {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConfig = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.fetchConfig();
      setConfig(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load config";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchConfig();
  }, [fetchConfig]);

  return {
    config,
    isLoading,
    error,
    refetch: fetchConfig,
  };
}

