"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, ArchiveRestore, ExternalLink, Plus, Radar, Radio } from "@/lib/icons";

import {
  CHANNEL_TYPE_GROUPS,
  ChannelTypeBadge,
  ChannelTypeIcon,
  getChannelTypeMeta,
} from "@/components/channels/channel-type-icon";
import { SourceReviewModal } from "@/components/channels/source-review-modal";
import { QueryError } from "@/components/shared/api-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  createChannel,
  fetchCandidates,
  fetchChannels,
  patchChannel,
} from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

function formatDisplayUrl(url: string) {
  try {
    const parsed = new URL(url.startsWith("http") ? url : `https://${url}`);
    const path = parsed.pathname === "/" ? "" : parsed.pathname;
    return `${parsed.hostname.replace(/^www\./, "")}${path}`;
  } catch {
    return url;
  }
}

export function AdvisorChannelsPanel({ personaId }: { personaId: string }) {
  const [channelType, setChannelType] = useState("youtube_channel");
  const [url, setUrl] = useState("");
  const [label, setLabel] = useState("");
  const [reviewOpen, setReviewOpen] = useState(false);
  const queryClient = useQueryClient();

  const channelsQuery = useQuery({
    queryKey: ["channels", personaId],
    queryFn: () => fetchChannels(personaId),
    enabled: Boolean(personaId),
  });

  const candidatesQuery = useQuery({
    queryKey: ["candidates", personaId],
    queryFn: () => fetchCandidates(personaId),
    enabled: Boolean(personaId),
  });

  const addMutation = useMutation({
    mutationFn: () => createChannel(personaId, { channel_type: channelType, url, label }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels", personaId] });
      setUrl("");
      setLabel("");
    },
  });

  const archiveMutation = useMutation({
    mutationFn: ({ channelId, archived }: { channelId: string; archived: boolean }) =>
      patchChannel(personaId, channelId, { archived }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["channels", personaId] }),
  });

  const channels = channelsQuery.data ?? [];
  const activeChannels = channels.filter((channel) => !channel.archived);
  const activeTypeMeta = getChannelTypeMeta(channelType);
  const candidates = candidatesQuery.data ?? [];

  return (
    <div className="space-y-6">
      <QueryError error={channelsQuery.error ?? candidatesQuery.error} />

      <SourceReviewModal
        personaId={personaId}
        open={reviewOpen}
        onOpenChange={setReviewOpen}
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="size-4" />
            Új csatorna
          </CardTitle>
          <CardDescription>
            Válaszd ki a platformot, add meg a linket, opcionálisan egy rövid nevet.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {CHANNEL_TYPE_GROUPS.map((group) => (
            <div key={group.id} className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {group.label}
              </p>
              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                {group.options.map((option) => (
                  <Button
                    key={option.value}
                    type="button"
                    variant="outline"
                    onClick={() => setChannelType(option.value)}
                    className={cn(
                      "h-auto items-start justify-start gap-3 rounded-lg p-3 text-left whitespace-normal",
                      channelType === option.value
                        ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                        : "hover:bg-muted/50",
                      !option.supported && "opacity-90"
                    )}
                  >
                    <ChannelTypeIcon type={option.value} size="sm" className="mt-0.5" />
                    <span className="min-w-0">
                      <span className="flex flex-wrap items-center gap-1.5">
                        <span className="text-sm font-medium">{option.label}</span>
                        {!option.supported ? (
                          <Badge variant="outline" className="text-[0.65rem]">
                            hamarosan
                          </Badge>
                        ) : null}
                      </span>
                      <span className="mt-0.5 block text-xs text-muted-foreground">
                        {option.description}
                      </span>
                    </span>
                  </Button>
                ))}
              </div>
            </div>
          ))}

          <div className="flex flex-wrap items-end gap-3 border-t pt-4">
            <div className="flex min-w-72 flex-1 flex-col gap-1.5">
              <Label className="text-xs font-medium text-muted-foreground">URL</Label>
              <Input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder={activeTypeMeta.urlHint || "https://…"}
              />
            </div>
            <div className="flex min-w-48 flex-1 flex-col gap-1.5">
              <Label className="text-xs font-medium text-muted-foreground">Név (opcionális)</Label>
              <Input
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="pl. Alex Hormozi YouTube"
              />
            </div>
            <Button
              type="button"
              onClick={() => addMutation.mutate()}
              disabled={!url || addMutation.isPending || !activeTypeMeta.supported}
            >
              <Plus className="size-4" />
              Hozzáadás
            </Button>
          </div>

          {!activeTypeMeta.supported ? (
            <p className="text-xs text-muted-foreground">
              A(z) <strong>{activeTypeMeta.label}</strong> discovery még fejlesztés alatt — egyelőre
              csak a támogatott platformok adhatók hozzá.
            </p>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Radar className="size-4" />
            Automatikus felderítés
          </CardTitle>
          <CardDescription>
            Social profil jelöltek keresése és ellenőrzése — ugyanaz a lépésenkénti folyamat, mint a
            terminálban (<code className="text-xs">review_sources.py</code>).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button type="button" variant="outline" onClick={() => setReviewOpen(true)}>
            Discovery indítása
          </Button>

          {candidates.length > 0 ? (
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground">
                Utolsó discovery: {candidates.length} jelölt (review után a jóváhagyottak alul
                jelennek meg).
              </p>
              <div className="space-y-2">
                {candidates.slice(0, 5).map((candidate) => (
                  <div
                    key={candidate.index}
                    className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm"
                  >
                    <ChannelTypeIcon type={candidate.platform} size="sm" />
                    <span className="min-w-0 truncate">{formatDisplayUrl(candidate.url)}</span>
                    <Badge variant="outline" className="ml-auto shrink-0 text-[0.65rem]">
                      {candidate.status}
                    </Badge>
                  </div>
                ))}
                {candidates.length > 5 ? (
                  <p className="text-xs text-muted-foreground">
                    +{candidates.length - 5} további jelölt — indítsd újra a review-t a teljes
                    listáért.
                  </p>
                ) : null}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Még nincs jelölt — indíts discovery-t, vagy adj hozzá csatornát kézzel fent.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Radio className="size-4" />
            Kiválasztott csatornák
          </CardTitle>
          <CardDescription>
            {activeChannels.length > 0
              ? `${activeChannels.length} aktív forrás — discovery és social scraping ezekből indul.`
              : "Még nincs kiválasztott csatorna ehhez a personához."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {channels.length === 0 ? (
            <div className="rounded-lg border border-dashed px-6 py-10 text-center text-sm text-muted-foreground">
              Futtass discovery-t, vagy adj hozzá legalább egy csatornát a fenti űrlapból.
            </div>
          ) : (
            channels.map((channel) => (
              <div
                key={channel.channel_id}
                className={cn(
                  "group flex gap-4 rounded-lg border p-4 transition-colors hover:bg-muted/30",
                  channel.archived && "opacity-60"
                )}
              >
                <ChannelTypeIcon type={channel.type} size="lg" />

                <div className="min-w-0 flex-1 space-y-2">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="truncate font-medium">
                          {channel.label || formatDisplayUrl(channel.url)}
                        </h3>
                        <ChannelTypeBadge type={channel.type} />
                        {channel.archived ? (
                          <Badge variant="outline">archivált</Badge>
                        ) : null}
                      </div>
                      <a
                        href={channel.url.startsWith("http") ? channel.url : `https://${channel.url}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex max-w-full items-center gap-1 text-sm text-primary hover:underline"
                      >
                        <span className="truncate">{formatDisplayUrl(channel.url)}</span>
                        <ExternalLink className="size-3 shrink-0 opacity-60" />
                      </a>
                    </div>

                    <Button
                      size="sm"
                      variant="outline"
                      className="shrink-0"
                      onClick={() =>
                        archiveMutation.mutate({
                          channelId: channel.channel_id,
                          archived: !channel.archived,
                        })
                      }
                    >
                      {channel.archived ? (
                        <>
                          <ArchiveRestore className="size-3.5" />
                          Visszaállítás
                        </>
                      ) : (
                        <>
                          <Archive className="size-3.5" />
                          Archiválás
                        </>
                      )}
                    </Button>
                  </div>

                  {channel.last_discovered_at ? (
                    <p className="text-xs text-muted-foreground">
                      Utolsó discovery: {formatDateTime(channel.last_discovered_at)}
                    </p>
                  ) : (
                    <p className="text-xs text-muted-foreground">Még nem futott discovery.</p>
                  )}
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
