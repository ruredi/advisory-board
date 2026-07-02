import { OverviewDashboard } from "@/components/overview/overview-dashboard";

export default function OverviewPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold">Áttekintés</h1>
        <p className="text-sm text-muted-foreground">
          Persona státuszok, aktív futások és költségek.
        </p>
      </div>
      <OverviewDashboard />
    </div>
  );
}
