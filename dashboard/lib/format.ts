const usdFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
});

export function formatUsd(value: number): string {
  return usdFormatter.format(value);
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

export function formatDurationSeconds(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }

  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}
