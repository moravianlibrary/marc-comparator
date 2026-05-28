import { useState, useEffect } from "react";

const STORAGE_KEY = "font-size";
const DEFAULT_SIZE = "default";

export const FONT_SIZE_OPTIONS = ["small", "default", "large", "x-large"] as const;

export type FontSizeKey = (typeof FONT_SIZE_OPTIONS)[number];

export function useFontSize() {
  const [size, setSize] = useState<FontSizeKey>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored && FONT_SIZE_OPTIONS.includes(stored as FontSizeKey)
      ? (stored as FontSizeKey)
      : DEFAULT_SIZE;
  });

  useEffect(() => {
    if (size === DEFAULT_SIZE) {
      document.documentElement.removeAttribute("data-font-size");
    } else {
      document.documentElement.setAttribute("data-font-size", size);
    }
    localStorage.setItem(STORAGE_KEY, size);
  }, [size]);

  return { size, setSize };
}
