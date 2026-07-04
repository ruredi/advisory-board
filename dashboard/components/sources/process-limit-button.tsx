"use client";

import {
  SourceLimitButton,
  buildSourceLimitOptions,
  type SourceLimitOption,
} from "@/components/sources/source-limit-button";

export type ProcessLimitOption = SourceLimitOption;

export const PROCESS_LIMIT_OPTIONS: ProcessLimitOption[] =
  buildSourceLimitOptions("feldolgozása");

export function ProcessLimitButton({
  disabled,
  isRunning,
  onStart,
}: {
  disabled?: boolean;
  isRunning?: boolean;
  onStart: (processLimit: number) => void;
}) {
  return (
    <SourceLimitButton
      options={PROCESS_LIMIT_OPTIONS}
      defaultValue={100}
      disabled={disabled}
      isRunning={isRunning}
      startLabel="Start"
      onStart={onStart}
    />
  );
}
