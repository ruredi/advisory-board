"use client";

import { usePersonaOptions } from "@/lib/hooks/use-persona-options";

export function PersonaSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (personaId: string) => void;
}) {
  const { personas, isLoading } = usePersonaOptions();
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-muted-foreground">Persona</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={isLoading}
        className="rounded-md border bg-background px-3 py-2 text-sm"
      >
        {personas.map((persona) => (
          <option key={persona.persona_id} value={persona.persona_id}>
            {persona.display_name}
          </option>
        ))}
      </select>
    </label>
  );
}
