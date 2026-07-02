"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, ArchiveRestore, ExternalLink, Plus, Radio } from "lucide-react";

import {
  CHANNEL_TYPE_GROUPS,
  ChannelTypeBadge,
  ChannelTypeIcon,
  getChannelTypeMeta,
} from "@/components/channels/channel-type-icon";
import { PageHeader } from "@/components/shared/page-header";
import { QueryError } from "@/components/shared/api-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { createChannel, fetchChannels, patchChannel } from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";
import { usePersonaPageState } from "@/lib/hooks/use-persona-page";
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

export function ChannelsPageClient() {
  const { personaId, setPersonaId } = usePersonaPageState();
  const [channelType, setChannelType] = useState("youtube_channel");
  const [url, setUrl] = useState("");
  const [label, setLabel] = useState("");
  const queryClient = useQueryClient();

  const channelsQuery = useQuery({
    queryKey: ["channels", personaId],
    queryFn: () => fetchChannels(personaId),
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
  const activeTypeMeta = getChannelTypeMeta(channelType);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Csatornák"
        description="YouTube, podcast, social és web források regisztrálása."
        personaId={personaId}
        onPersonaChange={setPersonaId}
      />

      <QueryError error={channelsQuery.error} />

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
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setChannelType(option.value)}
                    className={cn(
                      "flex items-start gap-3 rounded-lg border p-3 text-left transition-colors",
                      channelType === option.value
                        ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                        : "border-border hover:bg-muted/50",
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
                  </button>
                ))}
              </div>
            </div>
          ))}

          <div className="flex flex-wrap items-end gap-3 border-t pt-4">
            <label className="flex min-w-72 flex-1 flex-col gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">URL</span>
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder={activeTypeMeta.urlHint || "https://…"}
                className="rounded-md border bg-background px-3 py-2 text-sm"
              />
            </label>
            <label className="flex min-w-48 flex-1 flex-col gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">Név (opcionális)</span>
              <input
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="pl. Alex Hormozi YouTube"
                className="rounded-md border bg-background px-3 py-2 text-sm"
              />
            </label>
            <Button
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
            <Radio className="size-4" />
            Csatornák
          </CardTitle>
          <CardDescription>
            {channels.length > 0
              ? `${channels.length} regisztrált forrás — discovery ezekből gyűjti az új epizódokat.`
              : "Még nincs csatorna ehhez a personához."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {channels.length === 0 ? (
            <div className="rounded-lg border border-dashed px-6 py-10 text-center text-sm text-muted-foreground">
              Adj hozzá legalább egy YouTube csatornát vagy podcast feedet a fenti űrlapból.
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
