"use client";

import { ChevronDown, Loader } from "@/lib/icons";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ButtonGroup } from "@/components/ui/button-group";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

export type SourceLimitOption = {
  value: number;
  label: string;
  destructive?: boolean;
};

export const SOURCE_LIMIT_VALUES = [50, 100, 500, 1000, 0] as const;

export function buildSourceLimitOptions(
  action: "keresése" | "feldolgozása"
): SourceLimitOption[] {
  return SOURCE_LIMIT_VALUES.map((value) => ({
    value,
    label: value === 0 ? `Összes forrás ${action}` : `${value} forrás ${action}`,
    ...(value === 0 ? { destructive: true } : {}),
  }));
}

export function SourceLimitButton({
  options,
  defaultValue,
  disabled,
  isRunning,
  startLabel = "Start",
  onStart,
}: {
  options: SourceLimitOption[];
  defaultValue: number;
  disabled?: boolean;
  isRunning?: boolean;
  startLabel?: string;
  onStart: (limit: number) => void;
}) {
  const [selected, setSelected] = useState<number>(defaultValue);
  const selectedOption = options.find((option) => option.value === selected) ?? options[0];

  return (
    <ButtonGroup>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={disabled || isRunning}
            className={cn(
              "min-w-0 rounded-r-none border-r-0 pr-2 pl-2.5 font-normal shadow-none",
              selectedOption.destructive && "text-destructive"
            )}
          >
            <span className="max-w-[11rem] truncate">{selectedOption.label}</span>
            <ChevronDown className="size-3.5 shrink-0 opacity-60" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-[14rem]">
          {options.map((option) => (
            <DropdownMenuItem
              key={option.value}
              variant={option.destructive ? "destructive" : "default"}
              onSelect={() => setSelected(option.value)}
            >
              <span className="flex-1">{option.label}</span>
              {selected === option.value ? (
                <span className="text-xs text-muted-foreground">✓</span>
              ) : null}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
      <Button
        type="button"
        size="sm"
        disabled={disabled}
        onClick={() => onStart(selected)}
        className={cn(
          "-ml-px rounded-l-none shadow-none",
          selectedOption.destructive &&
            "bg-destructive text-white hover:bg-destructive/90 focus-visible:ring-destructive/30"
        )}
      >
        {isRunning ? (
          <>
            <Loader className="size-3.5 animate-spin" />
            Fut…
          </>
        ) : (
          startLabel
        )}
      </Button>
    </ButtonGroup>
  );
}
