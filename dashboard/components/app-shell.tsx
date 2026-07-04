"use client";

import { useEffect, useState } from "react";
import { Menu, Cancel as X } from "@/lib/icons";

import { SidebarNav } from "@/components/sidebar-nav";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function SidebarBrand() {
  return (
    <div className="px-6 py-5">
      <p className="font-heading text-sm font-semibold">Advisory Board</p>
      <p className="text-xs text-muted-foreground">Admin dashboard</p>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!mobileOpen) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
      }
    };

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);

    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [mobileOpen]);

  const closeMobile = () => setMobileOpen(false);

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-40 flex h-14 items-center gap-3 border-b bg-background px-4 md:hidden">
        <Button
          type="button"
          variant="outline"
          size="icon"
          aria-label={mobileOpen ? "Menü bezárása" : "Menü megnyitása"}
          aria-expanded={mobileOpen}
          aria-controls="app-sidebar"
          onClick={() => setMobileOpen((open) => !open)}
        >
          {mobileOpen ? <X className="size-4" /> : <Menu className="size-4" />}
        </Button>
        <SidebarBrand />
        <div className="ml-auto">
          <ThemeToggle />
        </div>
      </header>

      {mobileOpen ? (
        <Button
          type="button"
          variant="ghost"
          aria-label="Menü bezárása"
          className="fixed inset-0 z-40 h-auto rounded-none bg-black/50 md:hidden"
          onClick={closeMobile}
        />
      ) : null}

      <aside
        id="app-sidebar"
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-56 flex-col border-r bg-sidebar transition-transform duration-200 ease-in-out md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="hidden md:block">
          <SidebarBrand />
        </div>
        <div className="flex items-center justify-between border-b px-4 py-3 md:hidden">
          <p className="font-heading text-sm font-semibold">Menü</p>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="Menü bezárása"
            onClick={closeMobile}
          >
            <X className="size-4" />
          </Button>
        </div>
        <SidebarNav onNavigate={closeMobile} className="flex-1 overflow-y-auto" />
        <div className="hidden border-t p-3 md:block">
          <ThemeToggle />
        </div>
      </aside>

      <main className="min-w-0 flex-1 pt-14 md:ml-56 md:pt-0">
        <div className="px-6 py-8 md:px-10">{children}</div>
      </main>
    </>
  );
}
