const usdFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});

export function formatUsd(value: number): string {
  return usdFormatter.format(value);
}

export function formatCredits(value: number): string {
  return Math.round(value).toLocaleString("hu-HU");
}

export function formatDateOnly(value: string): string {
  const date = new Date(value.includes("T") ? value : `${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString("hu-HU", { dateStyle: "medium" });
}

/** SQLite `datetime('now')` UTC timestamps ("YYYY-MM-DD HH:MM:SS") rendered in local time. */
export function parseUtcTimestamp(value: string): number {
  const isoUtc = value.includes("T") ? value : `${value.replace(" ", "T")}Z`;
  return new Date(isoUtc).getTime();
}

export function formatDateTime(value: string): string {
  const date = parseUtcTimestamp(value);
  if (Number.isNaN(date)) {
    return value;
  }
  return new Date(date).toLocaleString("hu-HU", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

export function formatSourceDateStack(value: string | null): { date: string; time: string } | null {
  if (!value) return null;
  const ms = value.includes("T") ? new Date(value).getTime() : parseUtcTimestamp(value);
  if (Number.isNaN(ms)) {
    return { date: value, time: "" };
  }
  const date = new Date(ms);
  return {
    date: date.toLocaleDateString("hu-HU", { dateStyle: "medium" }),
    time: date.toLocaleTimeString("hu-HU", { hour: "2-digit", minute: "2-digit" }),
  };
}

export function formatDurationSeconds(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }

  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}
