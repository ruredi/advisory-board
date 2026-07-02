"use client";

import { useEffect, useState } from "react";

import { formatDurationSeconds, parseUtcTimestamp } from "@/lib/format";

export function useElapsedDuration(
  startedAt: string,
  finishedAt: string | null,
  isRunning: boolean,
): string {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!isRunning) {
      return;
    }

    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [isRunning]);

  const startMs = parseUtcTimestamp(startedAt);
  const endMs = finishedAt ? parseUtcTimestamp(finishedAt) : now;
  const elapsedSeconds = Math.max(0, Math.floor((endMs - startMs) / 1000));

  return formatDurationSeconds(elapsedSeconds);
}
