import { createElement, type JSX } from "react";
import { Globe, Mail, Podcast, Rss, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

type IconComponent = LucideIcon | ((props: { className?: string }) => JSX.Element);

export type ChannelTypeCategory = "media" | "social" | "web";

export interface ChannelTypeOption {
  value: string;
  label: string;
  description: string;
  urlHint: string;
  supported: boolean;
  iconClass: string;
  badgeClass: string;
}

export const CHANNEL_TYPE_GROUPS: {
  id: ChannelTypeCategory;
  label: string;
  options: ChannelTypeOption[];
}[] = [
  {
    id: "media",
    label: "Videó és podcast",
    options: [
      {
        value: "youtube_channel",
        label: "YouTube",
        description: "YouTube csatorna (@handle vagy /channel/…)",
        urlHint: "youtube.com/@AlexHormozi",
        supported: true,
        iconClass: "text-[#FF0000]",
        badgeClass: "bg-[#FF0000]/10 text-[#FF0000] border-[#FF0000]/20",
      },
      {
        value: "spotify_show",
        label: "Spotify",
        description: "Spotify show — RSS feloldás Apple Podcastsből",
        urlHint: "open.spotify.com/show/…",
        supported: true,
        iconClass: "text-[#1DB954]",
        badgeClass: "bg-[#1DB954]/10 text-[#1DB954] border-[#1DB954]/20",
      },
      {
        value: "apple_podcast",
        label: "Apple Podcasts",
        description: "Apple Podcasts show link",
        urlHint: "podcasts.apple.com/…/id…",
        supported: true,
        iconClass: "text-[#AF52DE]",
        badgeClass: "bg-[#AF52DE]/10 text-[#AF52DE] border-[#AF52DE]/20",
      },
      {
        value: "podcast_rss",
        label: "Podcast RSS",
        description: "Közvetlen RSS feed URL",
        urlHint: "rss.example.com/feed.xml",
        supported: true,
        iconClass: "text-orange-600",
        badgeClass: "bg-orange-500/10 text-orange-700 border-orange-500/20 dark:text-orange-400",
      },
      {
        value: "vimeo_channel",
        label: "Vimeo",
        description: "Vimeo csatorna vagy felhasználói oldal",
        urlHint: "vimeo.com/…",
        supported: false,
        iconClass: "text-[#1AB7EA]",
        badgeClass: "bg-[#1AB7EA]/10 text-[#1AB7EA] border-[#1AB7EA]/20",
      },
      {
        value: "soundcloud",
        label: "SoundCloud",
        description: "SoundCloud profil vagy playlist",
        urlHint: "soundcloud.com/…",
        supported: false,
        iconClass: "text-[#FF5500]",
        badgeClass: "bg-[#FF5500]/10 text-[#FF5500] border-[#FF5500]/20",
      },
    ],
  },
  {
    id: "social",
    label: "Social profilok",
    options: [
      {
        value: "x_profile",
        label: "X (Twitter)",
        description: "X/Twitter profil — timeline scraping",
        urlHint: "x.com/AlexHormozi",
        supported: false,
        iconClass: "text-foreground",
        badgeClass: "bg-foreground/10 text-foreground border-foreground/20",
      },
      {
        value: "instagram_profile",
        label: "Instagram",
        description: "Instagram profil — posztok gyűjtése",
        urlHint: "instagram.com/alexhormozi",
        supported: false,
        iconClass: "text-[#E4405F]",
        badgeClass: "bg-[#E4405F]/10 text-[#E4405F] border-[#E4405F]/20",
      },
      {
        value: "facebook_profile",
        label: "Facebook",
        description: "Facebook oldal vagy profil",
        urlHint: "facebook.com/…",
        supported: false,
        iconClass: "text-[#1877F2]",
        badgeClass: "bg-[#1877F2]/10 text-[#1877F2] border-[#1877F2]/20",
      },
      {
        value: "tiktok_profile",
        label: "TikTok",
        description: "TikTok profil",
        urlHint: "tiktok.com/@…",
        supported: false,
        iconClass: "text-foreground",
        badgeClass: "bg-foreground/10 text-foreground border-foreground/20",
      },
      {
        value: "threads_profile",
        label: "Threads",
        description: "Threads profil",
        urlHint: "threads.net/@…",
        supported: false,
        iconClass: "text-foreground",
        badgeClass: "bg-foreground/10 text-foreground border-foreground/20",
      },
      {
        value: "linkedin_profile",
        label: "LinkedIn",
        description: "LinkedIn személyes vagy céges profil",
        urlHint: "linkedin.com/in/…",
        supported: false,
        iconClass: "text-[#0A66C2]",
        badgeClass: "bg-[#0A66C2]/10 text-[#0A66C2] border-[#0A66C2]/20",
      },
    ],
  },
  {
    id: "web",
    label: "Web és hírlevél",
    options: [
      {
        value: "web_site",
        label: "Weboldal",
        description: "Blog vagy landing — linkek felfedezése",
        urlHint: "example.com/blog",
        supported: false,
        iconClass: "text-sky-600",
        badgeClass: "bg-sky-500/10 text-sky-700 border-sky-500/20 dark:text-sky-400",
      },
      {
        value: "substack",
        label: "Substack",
        description: "Substack newsletter archívum",
        urlHint: "name.substack.com",
        supported: false,
        iconClass: "text-[#FF6719]",
        badgeClass: "bg-[#FF6719]/10 text-[#FF6719] border-[#FF6719]/20",
      },
      {
        value: "medium",
        label: "Medium",
        description: "Medium publikáció vagy profil",
        urlHint: "medium.com/@…",
        supported: false,
        iconClass: "text-foreground",
        badgeClass: "bg-foreground/10 text-foreground border-foreground/20",
      },
      {
        value: "newsletter_rss",
        label: "Hírlevél RSS",
        description: "Beehiiv, Ghost, Mailchimp RSS feed",
        urlHint: "feed.example.com/rss",
        supported: false,
        iconClass: "text-violet-600",
        badgeClass: "bg-violet-500/10 text-violet-700 border-violet-500/20 dark:text-violet-400",
      },
    ],
  },
];

export const CHANNEL_TYPE_OPTIONS: ChannelTypeOption[] = CHANNEL_TYPE_GROUPS.flatMap(
  (group) => group.options
);

const TYPE_ALIASES: Record<string, string> = {
  youtube: "youtube_channel",
  spotify: "spotify_show",
  podcast: "podcast_rss",
  rss: "podcast_rss",
  web: "web_site",
  x: "x_profile",
  twitter: "x_profile",
  instagram: "instagram_profile",
  facebook: "facebook_profile",
  tiktok: "tiktok_profile",
  threads: "threads_profile",
  linkedin: "linkedin_profile",
};

function YoutubeIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.6 12 3.6 12 3.6s-7.5 0-9.4.5A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.5 9.4.5 9.4.5s7.5 0 9.4-.5a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8ZM9.7 15.5V8.5L15.8 12l-6.1 3.5Z" />
    </svg>
  );
}

function SpotifyIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.52 17.34c-.24.37-.74.48-1.1.24-3.02-1.85-6.82-2.27-11.3-1.24-.43.1-.86-.16-.96-.59-.1-.43.16-.86.59-.96 4.88-1.11 9.02-.64 12.42 1.4.37.22.48.74.25 1.15zm1.47-3.27c-.3.46-.93.61-1.39.31-3.46-2.12-8.73-2.73-12.82-1.49-.53.16-1.09-.14-1.25-.67-.16-.53.14-1.09.67-1.25 4.57-1.38 10.46-.71 14.43 1.7.46.28.61.91.36 1.4zm.13-3.4C15.26 8.03 8.84 7.88 5.16 9.18c-.64.24-1.34-.07-1.58-.71-.24-.64.07-1.34.71-1.58 4.24-1.58 11.29-1.4 15.63 1.55.58.34.77 1.08.43 1.66-.34.58-1.08.77-1.66.43z" />
    </svg>
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  );
}

function InstagramIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
    </svg>
  );
}

function FacebookIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
    </svg>
  );
}

function TikTokIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1v-3.5a6.37 6.37 0 0 0-.79-.05A6.34 6.34 0 0 0 3.15 15.2a6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.34-6.34V8.83a8.28 8.28 0 0 0 4.83 1.55V6.93a4.85 4.85 0 0 1-1.07-.24z" />
    </svg>
  );
}

function ThreadsIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.435 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.96-.065-1.182.408-2.256 1.33-3.023.88-.73 2.088-1.146 3.494-1.173 1.014-.02 1.947.118 2.787.41-.138-1.72-.696-2.943-1.663-3.633-1.003-.715-2.404-1.078-4.163-1.078h-.028c-1.163 0-2.274.232-3.3.69-.996.443-1.868 1.063-2.593 1.844l-1.518-1.437c.958-1.075 2.094-1.892 3.377-2.428 1.283-.536 2.647-.808 4.054-.808h.028c2.251 0 4.102.516 5.502 1.534 1.433 1.043 2.332 2.608 2.674 4.651 1.026.493 1.901 1.12 2.607 1.872.996 1.057 1.595 2.313 1.782 3.732.344 2.653-.666 5.295-2.757 7.343-1.865 1.83-4.323 2.636-7.433 2.662zM10.918 15.38c-.966.052-1.702.337-2.191.848-.356.373-.527.85-.482 1.343.043.473.276.883.657 1.155.381.272.885.402 1.464.369 1.019-.055 1.789-.455 2.289-1.19.37-.537.616-1.225.735-2.045a6.8 6.8 0 0 0-2.472-.48z" />
    </svg>
  );
}

function LinkedInIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  );
}

function SubstackIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M22.539 8.242H1.46V5.406h21.08v2.836zM1.46 10.812V24L12 18.11 22.54 24V10.812H1.46zM22.54 0H1.46v2.836h21.08V0z" />
    </svg>
  );
}

function MediumIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M13.54 12a6.8 6.8 0 0 1-6.77 6.82A6.8 6.8 0 0 1 0 12a6.8 6.8 0 0 1 6.77-6.82A6.8 6.8 0 0 1 13.54 12zM20.96 12c0 3.54-1.51 6.42-3.38 6.42-1.87 0-3.39-2.88-3.39-6.42s1.52-6.42 3.39-6.42 3.38 2.88 3.38 6.42zm5.39 0c0 3.17-.53 5.75-1.19 5.75-.66 0-1.19-2.58-1.19-5.75s.53-5.75 1.19-5.75c.66 0 1.19 2.58 1.19 5.75z" />
    </svg>
  );
}

function VimeoIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M23.977 6.416c-.105 2.338-1.739 5.543-4.894 9.609-3.268 4.247-6.026 6.37-8.29 6.37-1.409 0-2.578-1.294-3.553-3.881L5.322 11.4C4.603 8.816 3.834 7.522 3.01 7.522c-.179 0-.806.378-1.881 1.132L0 7.197c1.185-1.044 2.351-2.084 3.501-3.128C5.08 2.701 6.266 1.984 7.055 1.91c1.867-.18 3.016 1.1 3.447 3.838.466 2.953.789 4.789.971 5.507.539 2.45 1.131 3.674 1.776 3.674.502 0 1.256-.796 2.265-2.385 1.004-1.589 1.54-2.797 1.612-3.628.144-1.371-.395-2.061-1.614-2.061-.574 0-1.167.121-1.777.391 1.186-3.868 3.434-5.757 6.762-5.637 2.473.06 3.628 1.664 3.493 4.797l-.013.01z" />
    </svg>
  );
}

function SoundCloudIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M1.175 12.225c-.051 0-.094.046-.101.1l-.233 2.154.233 2.105c.007.058.05.098.101.098.05 0 .09-.04.099-.098l.262-2.105-.262-2.154c-.009-.06-.049-.1-.099-.1zm1.697.002c-.075 0-.135.06-.144.135l-.279 2.233.279 2.169c.009.077.069.135.144.135.075 0 .135-.058.144-.135l.315-2.169-.315-2.233c-.009-.075-.069-.135-.144-.135zm1.68.013c-.096 0-.175.079-.184.175l-.267 2.154.267 2.191c.009.096.088.175.184.175.095 0 .174-.079.183-.175l.303-2.191-.303-2.154c-.009-.096-.088-.175-.183-.175zm1.715.029c-.115 0-.209.094-.218.209l-.247 2.154.247 2.191c.009.115.103.209.218.209.114 0 .208-.094.217-.209l.279-2.191-.279-2.154c-.009-.115-.103-.209-.217-.209zm1.753.062c-.131 0-.239.108-.248.239l-.228 2.154.228 2.191c.009.131.117.239.248.239.13 0 .238-.108.247-.239l.258-2.191-.258-2.154c-.009-.131-.117-.239-.247-.239zm1.771.088c-.147 0-.267.12-.276.267l-.21 2.154.21 2.191c.009.147.129.267.276.267.146 0 .266-.12.275-.267l.24-2.191-.24-2.154c-.009-.147-.129-.267-.275-.267zm1.789.115c-.163 0-.295.132-.304.295l-.192 2.154.192 2.191c.009.163.141.295.304.295.162 0 .294-.132.303-.295l.222-2.191-.222-2.154c-.009-.163-.141-.295-.303-.295zm1.807.141c-.179 0-.324.145-.333.324l-.174 2.154.174 2.191c.009.179.154.324.333.324.178 0 .323-.145.332-.324l.204-2.191-.204-2.154c-.009-.179-.154-.324-.332-.324zm1.825.168c-.195 0-.353.158-.362.353l-.156 2.154.156 2.191c.009.195.167.353.362.353.194 0 .352-.158.361-.353l.186-2.191-.186-2.154c-.009-.195-.167-.353-.361-.353zm1.843.194c-.211 0-.382.171-.391.382l-.138 2.154.138 2.191c.009.211.18.382.391.382.21 0 .381-.171.39-.382l.168-2.191-.168-2.154c-.009-.211-.18-.382-.39-.382zm1.861.221c-.227 0-.411.184-.42.411l-.12 2.154.12 2.191c.009.227.193.411.42.411.226 0 .41-.184.419-.411l.15-2.191-.15-2.154c-.009-.227-.193-.411-.419-.411zm1.879.247c-.243 0-.44.197-.449.44l-.102 2.154.102 2.191c.009.243.206.44.449.44.242 0 .439-.197.448-.44l.132-2.191-.132-2.154c-.009-.243-.206-.44-.448-.44zm1.897.274c-.259 0-.469.21-.478.469l-.084 2.154.084 2.191c.009.259.219.469.478.469.258 0 .468-.21.477-.469l.114-2.191-.114-2.154c-.009-.259-.219-.469-.477-.469zm1.915.3c-.275 0-.498.223-.507.498l-.066 2.154.066 2.191c.009.275.232.498.507.498.274 0 .497-.223.506-.498l.096-2.191-.096-2.154c-.009-.275-.232-.498-.506-.498zm1.933.327c-.291 0-.527.236-.536.527l-.048 2.154.048 2.191c.009.291.245.527.536.527.29 0 .526-.236.535-.527l.078-2.191-.078-2.154c-.009-.291-.245-.527-.535-.527zm1.951.353c-.307 0-.556.249-.565.556l-.03 2.154.03 2.191c.009.307.258.556.565.556.306 0 .555-.249.564-.556l.06-2.191-.06-2.154c-.009-.307-.258-.556-.564-.556zm1.969.38c-.323 0-.585.262-.594.585l-.012 2.154.012 2.191c.009.323.271.585.594.585.322 0 .584-.262.593-.585l.042-2.191-.042-2.154c-.009-.323-.271-.585-.593-.585zm1.987.406c-.339 0-.614.275-.623.614v4.345c.009.339.284.614.623.614.338 0 .613-.275.622-.614v-4.345c-.009-.339-.284-.614-.622-.614zm1.987-.406c-.322 0-.584.262-.593.585l-.042 2.154.042 2.191c.009.323.271.585.593.585.307 0 .556-.249.565-.556l.03-2.191-.03-2.154c-.009-.307-.258-.556-.565-.556zm1.969-.353c-.306 0-.555.249-.564.556l-.06 2.154.06 2.191c.009.307.258.556.564.556.291 0 .527-.236.536-.527l.048-2.191-.048-2.154c-.009-.291-.245-.527-.536-.527zm1.951-.327c-.29 0-.526.236-.535.527l-.078 2.154.078 2.191c.009.291.245.527.535.527.275 0 .498-.223.507-.498l.066-2.191-.066-2.154c-.009-.275-.232-.498-.507-.498zm1.933-.3c-.274 0-.497.223-.506.498l-.096 2.154.096 2.191c.009.275.232.498.506.498.259 0 .469-.21.478-.469l.084-2.191-.084-2.154c-.009-.259-.219-.469-.478-.469zm1.915-.274c-.258 0-.468.21-.477.469l-.114 2.154.114 2.191c.009.259.219.469.477.469.243 0 .439-.197.448-.44l.102-2.191-.102-2.154c-.009-.243-.205-.44-.448-.44zm1.897-.247c-.242 0-.439.197-.448.44l-.132 2.154.132 2.191c.009.243.206.44.448.44.227 0 .411-.184.42-.411l.12-2.191-.12-2.154c-.009-.227-.193-.411-.42-.411zm1.879-.221c-.226 0-.41.184-.419.411l-.15 2.154.15 2.191c.009.227.193.411.419.411.211 0 .382-.171.391-.382l.138-2.191-.138-2.154c-.009-.211-.18-.382-.391-.382zm1.861-.194c-.21 0-.381.171-.39.382l-.168 2.154.168 2.191c.009.211.18.382.39.382.195 0 .353-.158.362-.353l.156-2.191-.156-2.154c-.009-.195-.167-.353-.362-.353zm1.843-.168c-.194 0-.352.158-.361.353l-.186 2.154.186 2.191c.009.195.167.353.361.353.179 0 .324-.145.333-.324l.174-2.191-.174-2.154c-.009-.179-.154-.324-.333-.324zm1.825-.141c-.178 0-.323.145-.332.324l-.204 2.154.204 2.191c.009.179.154.324.332.324.163 0 .295-.132.304-.295l.192-2.191-.192-2.154c-.009-.163-.141-.295-.304-.295zm1.807-.115c-.162 0-.294.132-.303.295l-.222 2.154.222 2.191c.009.163.141.295.303.295.147 0 .267-.12.276-.267l.21-2.191-.21-2.154c-.009-.147-.129-.267-.276-.267zm1.789-.088c-.146 0-.266.12-.275.267l-.24 2.154.24 2.191c.009.147.129.267.275.267.131 0 .239-.108.248-.239l.228-2.191-.228-2.154c-.009-.131-.117-.239-.248-.239zm1.771-.062c-.13 0-.238.108-.247.239l-.258 2.154.258 2.191c.009.131.117.239.247.239.115 0 .209-.094.218-.209l.247-2.191-.247-2.154c-.009-.115-.103-.209-.218-.209zm1.753-.029c-.114 0-.208.094-.217.209l-.279 2.154.279 2.191c.009.115.103.209.217.209.096 0 .175-.079.184-.175l.267-2.191-.267-2.154c-.009-.096-.088-.175-.184-.175zm1.715-.013c-.095 0-.174.079-.183.175l-.303 2.154.303 2.191c.009.096.088.175.183.175.075 0 .135-.058.144-.135l.279-2.169-.279-2.233c-.009-.075-.069-.135-.144-.135zm1.68-.002c-.074 0-.134.06-.143.135l-.315 2.233.315 2.169c.009.077.069.135.144.135.051 0 .091-.04.1-.098l.262-2.105-.262-2.154c-.009-.054-.052-.1-.101-.1z" />
    </svg>
  );
}

const ICONS: Record<string, IconComponent> = {
  youtube: YoutubeIcon,
  youtube_channel: YoutubeIcon,
  spotify: SpotifyIcon,
  spotify_show: SpotifyIcon,
  apple_podcast: Podcast,
  podcast_rss: Rss,
  rss: Rss,
  vimeo_channel: VimeoIcon,
  soundcloud: SoundCloudIcon,
  x_profile: XIcon,
  x: XIcon,
  twitter: XIcon,
  instagram_profile: InstagramIcon,
  instagram: InstagramIcon,
  facebook_profile: FacebookIcon,
  facebook: FacebookIcon,
  tiktok_profile: TikTokIcon,
  tiktok: TikTokIcon,
  threads_profile: ThreadsIcon,
  threads: ThreadsIcon,
  linkedin_profile: LinkedInIcon,
  linkedin: LinkedInIcon,
  web_site: Globe,
  web: Globe,
  substack: SubstackIcon,
  medium: MediumIcon,
  newsletter_rss: Mail,
};

function normalizeChannelType(type: string): string {
  return TYPE_ALIASES[type] ?? type;
}

function humanizeType(type: string): string {
  return type
    .replace(/_profile$/, "")
    .replace(/_channel$/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function getChannelTypeMeta(type: string): ChannelTypeOption {
  const normalized = normalizeChannelType(type);
  return (
    CHANNEL_TYPE_OPTIONS.find((option) => option.value === normalized) ?? {
      value: type,
      label: humanizeType(type),
      description: "",
      urlHint: "https://…",
      supported: false,
      iconClass: "text-muted-foreground",
      badgeClass: "bg-muted text-muted-foreground border-border",
    }
  );
}

function resolveIcon(type: string): IconComponent {
  const normalized = normalizeChannelType(type);
  return ICONS[type] ?? ICONS[normalized] ?? Globe;
}

function renderIcon(type: string, className: string) {
  return createElement(resolveIcon(type), { className });
}

export function resolveSourceIconType(
  sourceType: string,
  sourceUrl = "",
  channelUrl = "",
): string {
  const combined = `${sourceUrl} ${channelUrl}`.toLowerCase();
  const url = sourceUrl.toLowerCase();

  if (combined.includes("youtube.com") || combined.includes("youtu.be")) {
    return "youtube";
  }
  if (url.includes("x.com") || url.includes("twitter.com")) {
    return "x";
  }
  if (url.includes("instagram.com")) {
    return "instagram";
  }
  if (url.includes("facebook.com")) {
    return "facebook";
  }
  if (url.includes("linkedin.com")) {
    return "linkedin";
  }
  if (url.includes("tiktok.com")) {
    return "tiktok";
  }
  if (url.includes("threads.net")) {
    return "threads";
  }
  if (combined.includes("podcasts.apple.com")) {
    return "apple_podcast";
  }
  if (combined.includes("spotify.com") || combined.includes("flightcast.com")) {
    return "spotify";
  }
  if (sourceType === "podcast" || combined.includes(".mp3") || combined.includes(".m4a")) {
    return "podcast";
  }
  if (url.includes("substack.com")) {
    return "substack";
  }
  if (url.includes("medium.com")) {
    return "medium";
  }

  return sourceType || "web";
}

export function ChannelTypeIconMini({
  type,
  className,
}: {
  type: string;
  className?: string;
}) {
  const meta = getChannelTypeMeta(type);

  return (
    <span className={cn("inline-flex shrink-0 items-center", className)} aria-hidden>
      {renderIcon(type, cn("size-3.5", meta.iconClass))}
    </span>
  );
}

export function ChannelTypeIcon({
  type,
  size = "md",
  className,
}: {
  type: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const meta = getChannelTypeMeta(type);
  const sizeClass =
    size === "sm" ? "size-4" : size === "lg" ? "size-6" : "size-5";

  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-lg border",
        size === "sm" ? "size-7" : size === "lg" ? "size-11" : "size-9",
        meta.badgeClass,
        className
      )}
    >
      {renderIcon(type, cn(sizeClass, meta.iconClass))}
    </span>
  );
}

export function ChannelTypeBadge({ type }: { type: string }) {
  const meta = getChannelTypeMeta(type);

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        meta.badgeClass
      )}
    >
      {renderIcon(type, cn("size-3", meta.iconClass))}
      {meta.label}
    </span>
  );
}
