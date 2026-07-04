"use client";

import { Moon, Sun } from "@/lib/icons";
import { useTheme } from "@/components/theme-provider";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isDark = resolvedTheme === "dark";

  return (
    <Button
      type="button"
      variant="outline"
      size="icon"
      disabled={!mounted}
      aria-label={mounted ? (isDark ? "Világos mód" : "Sötét mód") : "Téma váltása"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
    >
      {mounted ? (
        isDark ? <Sun className="size-4" /> : <Moon className="size-4" />
      ) : (
        <Moon className="size-4 opacity-0" />
      )}
    </Button>
  );
}
