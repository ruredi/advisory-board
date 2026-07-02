"use client";

import { useQueries, useQuery } from "@tanstack/react-query";

import { fetchPersonaOverview, fetchPersonas } from "@/lib/api/client";

const OVERVIEW_POLL_MS = 5000;

export function usePersonas() {
  return useQuery({ queryKey: ["personas"], queryFn: fetchPersonas });
}

export function usePersonaOverview(personaId: string) {
  return useQuery({
    queryKey: ["persona-overview", personaId],
    queryFn: () => fetchPersonaOverview(personaId),
    enabled: Boolean(personaId),
    refetchInterval: OVERVIEW_POLL_MS,
  });
}

export function usePersonaOverviews(personaIds: string[]) {
  return useQueries({
    queries: personaIds.map((personaId) => ({
      queryKey: ["persona-overview", personaId],
      queryFn: () => fetchPersonaOverview(personaId),
      refetchInterval: OVERVIEW_POLL_MS,
    })),
  });
}
