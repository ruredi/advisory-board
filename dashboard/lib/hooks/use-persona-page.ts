"use client";

import { useState } from "react";

import { ALL_PERSONAS } from "@/lib/api/client";
import { usePersonaOptions } from "@/lib/hooks/use-persona-options";

/** Shared persona selection state for sub-pages (syncs after personas load). */
export function usePersonaPageState(options?: { defaultToAll?: boolean }) {
  const { defaultPersonaId, personas, isLoading } = usePersonaOptions();
  const fallback = (options?.defaultToAll ?? true) ? ALL_PERSONAS : defaultPersonaId;
  const [selectedPersonaId, setPersonaId] = useState<string | null>(null);
  const personaId = selectedPersonaId ?? fallback;

  return { personaId, setPersonaId, personas, isLoading };
}
