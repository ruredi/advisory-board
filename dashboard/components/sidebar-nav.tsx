"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Áttekintés" },
  { href: "/runs", label: "Futások" },
  { href: "/sources", label: "Források" },
  { href: "/memory", label: "Memória" },
  { href: "/advisors", label: "Advisorok" },
  { href: "/channels", label: "Forrás csatornák" },
  { href: "/review", label: "Forrás review" },
  { href: "/costs", label: "Költségek" },
  { href: "/logs", label: "Logok" },
] as const;

export function SidebarNav({
  onNavigate,
  className,
}: {
  onNavigate?: () => void;
  className?: string;
}) {
  const pathname = usePathname();

  return (
    <nav aria-label="Fő navigáció" className={cn("flex flex-col gap-1 p-3", className)}>
      {NAV_ITEMS.map((item) => {
        const isActive =
          item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
