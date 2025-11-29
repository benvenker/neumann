"use client";

import React, { createContext, useContext } from "react";

import { useConfig } from "@/lib/use-config";

type ConfigContextValue = ReturnType<typeof useConfig>;

const ConfigContext = createContext<ConfigContextValue | undefined>(undefined);

export function ConfigProvider({ children }: { children: React.ReactNode }) {
  const value = useConfig();
  return <ConfigContext.Provider value={value}>{children}</ConfigContext.Provider>;
}

export function useConfigContext(): ConfigContextValue {
  const ctx = useContext(ConfigContext);
  if (!ctx) {
    throw new Error("useConfigContext must be used within ConfigProvider");
  }
  return ctx;
}

