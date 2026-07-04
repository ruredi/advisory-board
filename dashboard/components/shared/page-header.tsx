"use client";

import { PersonaSelect } from "@/components/shared/persona-select";

export function PageHeader({
  title,
  description,
  personaId,
  onPersonaChange,
  personaAllowAll = true,
}: {
  title: string;
  description?: string;
  personaId?: string;
  onPersonaChange?: (id: string) => void;
  personaAllowAll?: boolean;
}) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="font-heading text-2xl font-semibold">{title}</h1>
        {description ? <p className="text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {personaId && onPersonaChange ? (
        <PersonaSelect value={personaId} onChange={onPersonaChange} allowAll={personaAllowAll} />
      ) : null}
    </div>
  );
}
