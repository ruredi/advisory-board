import type { ReactNode } from "react";

import {
  ChannelTypeIcon,
  ChannelTypeIconMini,
  resolveSourceIconType,
} from "@/components/channels/channel-type-icon";
import { cn } from "@/lib/utils";

export function SourceIdentity({
  title,
  sourceUrl,
  sourceType = "",
  channelUrl,
  subtitle,
  size = "sm",
  className,
}: {
  title: string | null | undefined;
  sourceUrl: string | null | undefined;
  sourceType?: string;
  channelUrl?: string | null;
  subtitle?: ReactNode;
  size?: "sm" | "md";
  className?: string;
}) {
  const label = title?.trim() || sourceUrl?.trim() || "Ismeretlen forrás";
  const iconType = resolveSourceIconType(sourceType, sourceUrl ?? "", channelUrl ?? "");

  return (
    <div className={cn("flex min-w-0 items-center gap-2.5", className)}>
      {size === "sm" ? (
        <ChannelTypeIconMini type={iconType} />
      ) : (
        <ChannelTypeIcon type={iconType} />
      )}
      <div className="min-w-0">
        <p className="truncate leading-snug font-medium">{label}</p>
        {subtitle ? <p className="truncate text-xs text-muted-foreground">{subtitle}</p> : null}
      </div>
    </div>
  );
}
