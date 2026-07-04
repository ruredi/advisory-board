"use client";

import { useState } from "react";

import { SourceReviewModal } from "@/components/channels/source-review-modal";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { ALL_PERSONAS } from "@/lib/api/client";
import { usePersonaPageState } from "@/lib/hooks/use-persona-page";

export function ReviewPageClient() {
  const { personaId, setPersonaId } = usePersonaPageState();
  const showAllPersonas = personaId === ALL_PERSONAS;
  const [reviewOpen, setReviewOpen] = useState(false);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Source review"
        description="Social profil jelöltek approve/reject — terminál-szerű lépésenkénti folyamat."
        personaId={personaId}
        onPersonaChange={setPersonaId}
      />

      {showAllPersonas ? (
        <p className="text-sm text-muted-foreground">
          Válassz egy advisort a source review indításához.
        </p>
      ) : (
        <>
          <SourceReviewModal
            personaId={personaId}
            open={reviewOpen}
            onOpenChange={setReviewOpen}
          />

          <Button type="button" variant="outline" onClick={() => setReviewOpen(true)}>
            Discovery indítása
          </Button>
        </>
      )}
    </div>
  );
}
