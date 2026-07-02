"use client";

import { useState } from "react";

import { usePersonaOptions } from "@/lib/hooks/use-persona-options";

/** Shared persona selection state for sub-pages (syncs after personas load). */
export function usePersonaPageState() {
  const { defaultPersonaId, personas, isLoading } = usePersonaOptions();
  const [selectedPersonaId, setPersonaId] = useState<string | null>(null);
  const personaId = selectedPersonaId ?? defaultPersonaId;

  return { personaId, setPersonaId, personas, isLoading };
}
