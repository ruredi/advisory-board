import { redirect } from "next/navigation";

export default function ChannelsPage() {
  redirect("/advisors?tab=channels");
}
