export const THEME_COOKIE = "theme";
export const THEME_STORAGE_KEY = "theme";

export type Theme = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export function isTheme(value: string | undefined | null): value is Theme {
  return value === "light" || value === "dark" || value === "system";
}

export function themeCookieValue(theme: Theme) {
  return `${THEME_COOKIE}=${theme}; path=/; max-age=31536000; SameSite=Lax`;
}

export function htmlThemeClass(theme: Theme | undefined): string | undefined {
  if (theme === "dark") return "dark";
  if (theme === "light") return "light";
  return undefined;
}
