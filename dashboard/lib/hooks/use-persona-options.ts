"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchPersonas } from "@/lib/api/client";

export function usePersonaOptions() {
  const query = useQuery({ queryKey: ["personas"], queryFn: fetchPersonas });
  return {
    personas: query.data ?? [],
    defaultPersonaId: query.data?.[0]?.persona_id ?? "hormozi",
    isLoading: query.isLoading,
  };
}
