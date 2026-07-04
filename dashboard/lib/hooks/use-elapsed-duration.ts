"use client";

import { useEffect, useState } from "react";

import { formatDurationSeconds, parseUtcTimestamp } from "@/lib/format";

export function useElapsedDuration(
  startedAt: string,
  stoppedAt: string | null,
  isRunning: boolean,
  fixedDurationSeconds?: number,
): string {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!isRunning) {
      return;
    }

    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [isRunning]);

  if (!isRunning && fixedDurationSeconds !== undefined) {
    return formatDurationSeconds(fixedDurationSeconds);
  }

  const startMs = parseUtcTimestamp(startedAt);
  const endMs = stoppedAt ? parseUtcTimestamp(stoppedAt) : now;
  const elapsedSeconds = Math.max(0, Math.floor((endMs - startMs) / 1000));

  return formatDurationSeconds(elapsedSeconds);
}
