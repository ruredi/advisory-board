"use client";

import {
  SourceLimitButton,
  buildSourceLimitOptions,
  type SourceLimitOption,
} from "@/components/sources/source-limit-button";

export type DiscoveryLimitOption = SourceLimitOption;

export const DISCOVERY_LIMIT_OPTIONS: DiscoveryLimitOption[] =
  buildSourceLimitOptions("keresése");

export function DiscoveryLimitButton({
  disabled,
  isRunning,
  onStart,
}: {
  disabled?: boolean;
  isRunning?: boolean;
  onStart: (discoveryLimit: number) => void;
}) {
  return (
    <SourceLimitButton
      options={DISCOVERY_LIMIT_OPTIONS}
      defaultValue={100}
      disabled={disabled}
      isRunning={isRunning}
      startLabel="Start"
      onStart={onStart}
    />
  );
}
