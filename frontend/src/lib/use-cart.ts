"use client";

import { useCallback, useMemo, useState } from "react";

import { CartItem } from "./types";

export interface CartTotals {
  textTokens: number;
  imageTokens: number;
  compressionRatio: number | null;
}

export interface UseCartState {
  items: CartItem[];
  totals: CartTotals;
  add: (item: CartItem) => void;
  remove: (chunkId: string) => void;
  clear: () => void;
  reorder: (fromIndex: number, toIndex: number) => void;
  isInCart: (chunkId: string) => boolean;
}

const IMAGE_TOKENS_PER_PAGE = 258;

function estimateTextTokens(text: string | undefined): number {
  if (!text) return 0;
  return Math.ceil(text.length / 4);
}

function estimateImageTokens(pageUris: string[] | undefined): number {
  if (!pageUris || !pageUris.length) return 0;
  return pageUris.length * IMAGE_TOKENS_PER_PAGE;
}

function computeTotals(items: CartItem[]): CartTotals {
  const textTokens = items.reduce((acc, item) => acc + estimateTextTokens(item.text), 0);
  const imageTokens = items.reduce((acc, item) => acc + estimateImageTokens(item.page_uris), 0);
  const compressionRatio = textTokens > 0 ? imageTokens / textTokens : null;
  return { textTokens, imageTokens, compressionRatio };
}

export function useCart(): UseCartState {
  const [items, setItems] = useState<CartItem[]>([]);

  const totals = useMemo(() => computeTotals(items), [items]);

  const add = useCallback((item: CartItem) => {
    setItems((prev) => {
      if (prev.some((it) => it.chunk_id === item.chunk_id)) return prev;
      return [...prev, item];
    });
  }, []);

  const remove = useCallback((chunkId: string) => {
    setItems((prev) => prev.filter((it) => it.chunk_id !== chunkId));
  }, []);

  const clear = useCallback(() => {
    setItems([]);
  }, []);

  const reorder = useCallback((fromIndex: number, toIndex: number) => {
    setItems((prev) => {
      const next = [...prev];
      if (fromIndex < 0 || fromIndex >= next.length || toIndex < 0 || toIndex >= next.length) {
        return next;
      }
      const [moved] = next.splice(fromIndex, 1);
      next.splice(toIndex, 0, moved);
      return next;
    });
  }, []);

  const isInCart = useCallback(
    (chunkId: string) => items.some((it) => it.chunk_id === chunkId),
    [items],
  );

  return {
    items,
    totals,
    add,
    remove,
    clear,
    reorder,
    isInCart,
  };
}

