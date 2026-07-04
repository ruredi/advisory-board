import type { ReactNode } from "react";
import Link from "next/link";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function MetricCard({
  label,
  value,
  hint,
  tone = "default",
  href,
  onClick,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "default" | "danger" | "success";
  href?: string;
  onClick?: () => void;
}) {
  const content = (
    <CardContent>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p
        className={cn(
          "font-heading text-xl font-semibold tabular-nums",
          tone === "danger" && "text-red-500",
          tone === "success" && "text-emerald-600 dark:text-emerald-400"
        )}
      >
        {value}
      </p>
      {hint ? <p className="truncate text-xs text-muted-foreground">{hint}</p> : null}
    </CardContent>
  );

  const interactive = Boolean(href || onClick);
  const cardClassName = cn(
    interactive && "transition-shadow hover:shadow-sm hover:ring-foreground/20"
  );

  if (href) {
    return (
      <Link href={href} className="block">
        <Card size="sm" className={cardClassName}>
          {content}
        </Card>
      </Link>
    );
  }

  if (onClick) {
    return (
      <Button
        type="button"
        variant="ghost"
        onClick={onClick}
        className="block h-auto w-full p-0 text-left hover:bg-transparent"
      >
        <Card size="sm" className={cardClassName}>
          {content}
        </Card>
      </Button>
    );
  }

  return <Card size="sm">{content}</Card>;
}
