import { createElement, type ComponentType } from "react";
import { FileText, Globe, Image, Mic, Share2 } from "lucide-react";
import { FaLinkedin } from "react-icons/fa6";
import {
  SiApplepodcasts,
  SiFacebook,
  SiInstagram,
  SiSpotify,
  SiX,
  SiYoutube,
} from "react-icons/si";

import { cn } from "@/lib/utils";

type IconProps = { className?: string };

interface PlatformMeta {
  icon: ComponentType<IconProps>;
  colorClass: string;
}

const PLATFORM_META: Record<string, PlatformMeta> = {
  YouTube: { icon: SiYoutube, colorClass: "text-[#FF0000]" },
  Spotify: { icon: SiSpotify, colorClass: "text-[#1DB954]" },
  "Apple Podcasts": { icon: SiApplepodcasts, colorClass: "text-[#AF52DE]" },
  Podcast: { icon: Mic, colorClass: "text-orange-600" },
  X: { icon: SiX, colorClass: "text-foreground" },
  Instagram: { icon: SiInstagram, colorClass: "text-[#E4405F]" },
  Facebook: { icon: SiFacebook, colorClass: "text-[#1877F2]" },
  LinkedIn: { icon: FaLinkedin, colorClass: "text-[#0A66C2]" },
  Social: { icon: Share2, colorClass: "text-muted-foreground" },
  Web: { icon: Globe, colorClass: "text-sky-600" },
  PDF: { icon: FileText, colorClass: "text-red-600" },
  Image: { icon: Image, colorClass: "text-violet-600" },
};

const DEFAULT_META: PlatformMeta = {
  icon: Globe,
  colorClass: "text-muted-foreground",
};

export function getPlatformMeta(platform: string): PlatformMeta {
  return PLATFORM_META[platform] ?? DEFAULT_META;
}

export function PlatformIcon({
  platform,
  className,
}: {
  platform: string;
  className?: string;
}) {
  const meta = getPlatformMeta(platform);
  return createElement(meta.icon, { className: cn("size-4 shrink-0", meta.colorClass, className) });
}

export function PlatformFilterButton({
  platform,
  count,
  active,
  onClick,
}: {
  platform: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  const meta = getPlatformMeta(platform);

  return (
    <button
      type="button"
      title={`${platform} · ${count.toLocaleString("hu-HU")} unit`}
      aria-label={`${platform}, ${count} unit`}
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "inline-flex size-8 items-center justify-center rounded-md border transition-colors",
        active
          ? "border-primary bg-primary/10 ring-1 ring-primary/30"
          : "border-border bg-background hover:bg-muted/80"
      )}
    >
      {createElement(meta.icon, { className: cn("size-4", meta.colorClass) })}
    </button>
  );
}
