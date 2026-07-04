export type AdvisorTab = "profile" | "config-files" | "channels";

export function parseAdvisorTab(value: string | null | undefined): AdvisorTab {
  if (value === "config-files" || value === "channels") return value;
  return "profile";
}
