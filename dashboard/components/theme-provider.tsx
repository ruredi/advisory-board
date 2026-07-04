"use client";

import { createContext, useContext, useLayoutEffect, useMemo, useState } from "react";

import {
  THEME_STORAGE_KEY,
  type ResolvedTheme,
  type Theme,
  themeCookieValue,
} from "@/lib/theme";

function getSystemTheme(): ResolvedTheme {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function resolveTheme(theme: Theme): ResolvedTheme {
  return theme === "system" ? getSystemTheme() : theme;
}

function applyTheme(theme: Theme, resolved: ResolvedTheme) {
  const root = document.documentElement;
  root.classList.remove("light", "dark");
  if (theme === "dark") {
    root.classList.add("dark");
  } else if (theme === "light") {
    root.classList.add("light");
  }
  root.style.colorScheme = resolved;
}

function readStoredTheme(): Theme {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") {
      return stored;
    }
  } catch {
    // localStorage unavailable
  }
  return "system";
}

function persistTheme(theme: Theme) {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // localStorage unavailable
  }
  document.cookie = themeCookieValue(theme);
}

type ThemeContextValue = {
  theme: Theme | undefined;
  resolvedTheme: ResolvedTheme | undefined;
  setTheme: (theme: Theme) => void;
};

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme | undefined>(undefined);
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme | undefined>(undefined);

  useLayoutEffect(() => {
    const stored = readStoredTheme();
    const resolved = resolveTheme(stored);
    setThemeState(stored);
    setResolvedTheme(resolved);
    applyTheme(stored, resolved);
    persistTheme(stored);
  }, []);

  useLayoutEffect(() => {
    if (!theme) return;

    const resolved = resolveTheme(theme);
    setResolvedTheme(resolved);
    applyTheme(theme, resolved);
    persistTheme(theme);

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (theme !== "system") return;
      const next = getSystemTheme();
      setResolvedTheme(next);
      applyTheme("system", next);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [theme]);

  const setTheme = (next: Theme) => setThemeState(next);

  const value = useMemo(
    () => ({ theme, resolvedTheme, setTheme }),
    [theme, resolvedTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return ctx;
}
