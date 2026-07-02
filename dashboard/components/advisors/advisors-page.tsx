"use client";

import Image from "next/image";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  createAdvisorConfigFile,
  deploySoul,
  fetchAdvisor,
  fetchAdvisors,
  fetchAdvisorConfigFile,
  fetchAdvisorConfigFiles,
  fetchSoul,
  saveAdvisorConfigFile,
  uploadAdvisorPhoto,
} from "@/lib/api/client";
import type { AdvisorConfigFileItem } from "@/lib/api/types";

type AdvisorTab = "profile" | "config-files";

function advisorInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function AdvisorPhoto({
  advisorId,
  advisorName,
  photoUrl,
}: {
  advisorId: string;
  advisorName: string;
  photoUrl: string | null;
}) {
  const queryClient = useQueryClient();
  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadAdvisorPhoto(advisorId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["advisors"] });
      queryClient.invalidateQueries({ queryKey: ["advisor", advisorId] });
    },
  });

  return (
    <div className="space-y-2">
      <label
        className="group relative flex size-24 cursor-pointer items-center justify-center overflow-hidden rounded-2xl border bg-muted text-lg font-semibold"
        title="Advisor fotó feltöltése"
      >
        {photoUrl ? (
          <Image
            src={photoUrl}
            alt={`${advisorName} fotó`}
            width={96}
            height={96}
            className="size-full object-cover"
          />
        ) : (
          <span>{advisorInitials(advisorName) || "?"}</span>
        )}
        <span className="absolute inset-x-0 bottom-0 bg-black/60 px-2 py-1 text-center text-[11px] font-medium text-white opacity-0 transition-opacity group-hover:opacity-100">
          Fotó feltöltése
        </span>
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif,image/avif"
          className="sr-only"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) uploadMutation.mutate(file);
            event.currentTarget.value = "";
          }}
        />
      </label>
      {uploadMutation.isError ? (
        <p className="max-w-48 text-xs text-destructive">Nem sikerült feltölteni a képet.</p>
      ) : null}
    </div>
  );
}

function AdvisorConfigFileEditor({
  advisorId,
  file,
  initialContent,
}: {
  advisorId: string;
  file: AdvisorConfigFileItem;
  initialContent: string;
}) {
  const [content, setContent] = useState(initialContent);
  const queryClient = useQueryClient();
  const saveMutation = useMutation({
    mutationFn: () => saveAdvisorConfigFile(advisorId, file.key, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["advisor-config-files", advisorId] });
      queryClient.invalidateQueries({ queryKey: ["advisor-config-file", advisorId, file.key] });
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs text-muted-foreground">
          <span className="font-mono">{file.path}</span>
          {file.shared ? <span> · közös config</span> : null}
        </div>
        <Button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
        >
          Mentés
        </Button>
      </div>
      <textarea
        value={content}
        onChange={(event) => setContent(event.target.value)}
        className="min-h-[32rem] w-full rounded-md border bg-background p-3 font-mono text-xs"
        aria-label={`${file.label} szerkesztése`}
      />
      {saveMutation.isError ? (
        <p className="text-sm text-destructive">
          Mentés nem sikerült:{" "}
          {saveMutation.error instanceof Error ? saveMutation.error.message : "érvénytelen fájl"}
        </p>
      ) : null}
    </div>
  );
}

function AdvisorConfigFilesPanel({ advisorId }: { advisorId: string }) {
  const [selectedFileKey, setSelectedFileKey] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const filesQuery = useQuery({
    queryKey: ["advisor-config-files", advisorId],
    queryFn: () => fetchAdvisorConfigFiles(advisorId),
  });
  const files = filesQuery.data ?? [];
  const selectedKey = selectedFileKey ?? files[0]?.key ?? "";
  const selectedFile = files.find((file) => file.key === selectedKey) ?? null;
  const fileQuery = useQuery({
    queryKey: ["advisor-config-file", advisorId, selectedKey],
    queryFn: () => fetchAdvisorConfigFile(advisorId, selectedKey),
    enabled: Boolean(selectedKey),
  });
  const createMutation = useMutation({
    mutationFn: (fileKey: string) => createAdvisorConfigFile(advisorId, fileKey),
    onSuccess: (_data, fileKey) => {
      queryClient.invalidateQueries({ queryKey: ["advisor-config-files", advisorId] });
      queryClient.invalidateQueries({ queryKey: ["advisor-config-file", advisorId, fileKey] });
    },
  });

  return (
    <div className="grid gap-4 xl:grid-cols-[18rem_1fr]">
      <Card>
        <CardHeader>
          <CardTitle>Config fájlok</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {filesQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Config fájlok betöltése...</p>
          ) : null}
          {files.map((file) => (
            <button
              key={file.key}
              type="button"
              onClick={() => setSelectedFileKey(file.key)}
              className={`w-full rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                selectedKey === file.key ? "bg-primary text-primary-foreground" : "hover:bg-muted"
              }`}
            >
              <span className="block font-medium">{file.label}</span>
              <span className="block truncate text-xs opacity-75">{file.path}</span>
              {!file.exists ? <span className="mt-1 block text-xs opacity-75">Még nincs létrehozva</span> : null}
            </button>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{selectedFile?.label ?? "Config fájl"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {selectedFile && !selectedFile.exists ? (
            <div className="space-y-3 rounded-md border p-4">
              <div>
                <p className="font-medium">Ez a config fájl még nem létezik.</p>
                <p className="text-sm text-muted-foreground">
                  Hozz létre egy induló fájlt, utána itt szerkeszthető lesz.
                </p>
              </div>
              {selectedFile.can_create ? (
                <Button
                  onClick={() => createMutation.mutate(selectedFile.key)}
                  disabled={createMutation.isPending}
                >
                  Config fájl létrehozása
                </Button>
              ) : null}
            </div>
          ) : null}

          {fileQuery.isLoading && selectedFile?.exists ? (
            <p className="text-sm text-muted-foreground">Config fájl betöltése...</p>
          ) : null}

          {fileQuery.data?.content !== null && fileQuery.data?.content !== undefined ? (
            <AdvisorConfigFileEditor
              key={`${advisorId}:${fileQuery.data.key}:${fileQuery.data.path}`}
              advisorId={advisorId}
              file={fileQuery.data}
              initialContent={fileQuery.data.content}
            />
          ) : null}

          {fileQuery.isError ? (
            <p className="text-sm text-destructive">Nem sikerült betölteni a config fájlt.</p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

export function AdvisorsPageClient() {
  const [advisorId, setAdvisorId] = useState("jobs");
  const [activeTab, setActiveTab] = useState<AdvisorTab>("profile");

  const advisorsQuery = useQuery({ queryKey: ["advisors"], queryFn: fetchAdvisors });
  const advisorQuery = useQuery({
    queryKey: ["advisor", advisorId],
    queryFn: () => fetchAdvisor(advisorId),
    enabled: Boolean(advisorId),
  });
  const soulQuery = useQuery({
    queryKey: ["soul", advisorId],
    queryFn: () => fetchSoul(advisorId),
    enabled: Boolean(advisorId),
  });

  const deployMutation = useMutation({
    mutationFn: () => deploySoul(advisorId),
    onSuccess: () => soulQuery.refetch(),
  });

  const deployed = soulQuery.data?.deployed ?? "";
  const rendered = soulQuery.data?.rendered ?? "";
  const differs = deployed.trim() !== rendered.trim();
  const selectedAdvisorName = advisorQuery.data?.config.name ?? advisorId;
  const selectedPhotoUrl = advisorQuery.data?.photo_url ?? null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Advisorok"
        description="Advisor profil, Hermes deploy és forrás/memória konfiguráció egy helyen."
      />

      <div className="flex flex-wrap gap-2">
        {(advisorsQuery.data ?? []).map((advisor) => (
          <Button
            key={advisor.advisor_id}
            variant={advisorId === advisor.advisor_id ? "default" : "outline"}
            size="sm"
            onClick={() => setAdvisorId(advisor.advisor_id)}
            className="gap-2"
          >
            {advisor.photo_url ? (
              <Image
                src={advisor.photo_url}
                alt=""
                width={20}
                height={20}
                className="size-5 rounded-full object-cover"
              />
            ) : (
              <span className="flex size-5 items-center justify-center rounded-full bg-muted text-[10px] text-muted-foreground">
                {advisorInitials(advisor.name) || "?"}
              </span>
            )}
            {advisor.name}
          </Button>
        ))}
      </div>

      {advisorQuery.data ? (
        <Card>
          <CardHeader>
            <CardTitle>{advisorQuery.data.config.name}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 text-sm sm:flex-row">
            <AdvisorPhoto
              advisorId={advisorId}
              advisorName={advisorQuery.data.config.name}
              photoUrl={selectedPhotoUrl}
            />
            <div className="space-y-2">
              <p>{advisorQuery.data.config.role}</p>
              <div className="flex flex-wrap gap-1">
                {(advisorQuery.data.config.core_traits as string[]).map((trait) => (
                  <Badge key={trait} variant="secondary">{trait}</Badge>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                Kattints a fotóra az advisor képének feltöltéséhez.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <div className="flex flex-wrap gap-2 border-b">
        <Button
          variant={activeTab === "profile" ? "default" : "ghost"}
          size="sm"
          onClick={() => setActiveTab("profile")}
        >
          Profil & deploy
        </Button>
        <Button
          variant={activeTab === "config-files" ? "default" : "ghost"}
          size="sm"
          onClick={() => setActiveTab("config-files")}
        >
          Config fájlok
        </Button>
      </div>

      {activeTab === "profile" ? (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Button onClick={() => deployMutation.mutate()} disabled={deployMutation.isPending}>
              Deploy SOUL.md → ~/.hermes/profiles/{advisorId}/
            </Button>
            {soulQuery.data?.deployed_exists ? (
              differs ? (
                <Badge variant="outline">Diff: deploy ≠ render</Badge>
              ) : (
                <Badge>Egyezik a deployolt verzióval</Badge>
              )
            ) : (
              <Badge variant="outline">Még nincs deployolt SOUL</Badge>
            )}
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Render preview</CardTitle></CardHeader>
              <CardContent>
                <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap text-xs">{rendered}</pre>
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Deployolt SOUL</CardTitle></CardHeader>
              <CardContent>
                <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap text-xs">
                  {deployed || "(nincs deployolt fájl)"}
                </pre>
              </CardContent>
            </Card>
          </div>
        </div>
      ) : null}

      {activeTab === "config-files" ? (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            {selectedAdvisorName} összes ismert konfigurációs fájlja egy helyen:
            profil, source/memória YAML, jóváhagyott profilok és csatorna registry.
          </p>
          <AdvisorConfigFilesPanel key={advisorId} advisorId={advisorId} />
        </div>
      ) : null}
    </div>
  );
}
