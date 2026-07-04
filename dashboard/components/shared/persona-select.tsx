"use client";

import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ALL_PERSONAS } from "@/lib/api/client";
import { usePersonaOptions } from "@/lib/hooks/use-persona-options";

export function PersonaSelect({
  value,
  onChange,
  allowAll = false,
}: {
  value: string;
  onChange: (personaId: string) => void;
  allowAll?: boolean;
}) {
  const { personas, isLoading } = usePersonaOptions();
  return (
    <div className="flex flex-col gap-1 text-sm">
      <Label className="text-muted-foreground">Persona</Label>
      <Select value={value} onValueChange={onChange} disabled={isLoading}>
        <SelectTrigger className="w-full min-w-48">
          <SelectValue placeholder="Persona kiválasztása" />
        </SelectTrigger>
        <SelectContent>
          {allowAll ? (
            <SelectItem value={ALL_PERSONAS}>Összes advisor</SelectItem>
          ) : null}
          {personas.map((persona) => (
            <SelectItem key={persona.persona_id} value={persona.persona_id}>
              {persona.display_name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
