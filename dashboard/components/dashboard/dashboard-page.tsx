"use client";

import { PageHeader } from "@/components/shared/page-header";
import { ALL_PERSONAS } from "@/lib/api/client";
import { usePersonaPageState } from "@/lib/hooks/use-persona-page";

import { DashboardHealthStrip } from "./dashboard-health-strip";
import { SourceMemoryWorkbench } from "./source-memory-workbench";
import { LiveActivityRail } from "./live-activity-rail";

export function DashboardPageClient() {
  const { personaId, setPersonaId } = usePersonaPageState();
  const showAllPersonas = personaId === ALL_PERSONAS;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Egy helyen minden, ami a pipeline állapotáról, a forrásokról és a memóriáról fontos."
        personaId={personaId}
        onPersonaChange={setPersonaId}
      />

      {personaId ? (
        <>
          <DashboardHealthStrip personaId={personaId} showAllPersonas={showAllPersonas} />
          <SourceMemoryWorkbench personaId={personaId} showAllPersonas={showAllPersonas} />
          <LiveActivityRail personaId={personaId} showAllPersonas={showAllPersonas} />
        </>
      ) : null}
    </div>
  );
}
