"use client";

import { useQuery } from "@tanstack/react-query";

import { Card, CardContent } from "@/components/ui/card";

async function fetchApiHealth(): Promise<{ status: string; api_version?: number; route_count: number }> {
  const response = await fetch("/api/health");
  if (!response.ok) throw new Error("API nem elérhető");
  return (await response.json()) as { status: string; api_version?: number; route_count: number };
}

export function ApiGuard({ children }: { children: React.ReactNode }) {
  const healthQuery = useQuery({
    queryKey: ["api-health"],
    queryFn: fetchApiHealth,
    retry: 1,
    refetchInterval: 30000,
  });

  const staleApi =
    healthQuery.isSuccess &&
    (healthQuery.data.api_version !== 2 || healthQuery.data.route_count < 10);

  return (
    <>
      {healthQuery.isError ? (
        <Card className="mb-6 border-destructive/40 bg-destructive/5">
          <CardContent className="py-4 text-sm text-destructive">
            A dashboard API nem elérhető a 8100-as porton. Indítsd:{" "}
            <code className="font-mono">make api</code> vagy{" "}
            <code className="font-mono">make dev</code>
          </CardContent>
        </Card>
      ) : null}
      {staleApi ? (
        <Card className="mb-6 border-amber-500/40 bg-amber-500/5">
          <CardContent className="py-4 text-sm">
            Régi API fut ({healthQuery.data.route_count} endpoint). Állítsd le és indítsd újra:{" "}
            <code className="font-mono">pkill -f &quot;uvicorn api.main&quot;; make api</code>
          </CardContent>
        </Card>
      ) : null}
      {children}
    </>
  );
}

export function QueryError({ error }: { error: Error | null | undefined }) {
  if (!error) return null;
  return (
    <p role="alert" className="text-sm text-destructive">
      {error.message.includes("404") || error.message.includes("Not Found")
        ? "API endpoint nem található — indítsd újra a backendet: make api"
        : error.message}
    </p>
  );
}
