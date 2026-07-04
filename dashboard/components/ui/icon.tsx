import type { ComponentType, SVGProps } from "react";
import { HugeiconsIcon, type IconSvgElement } from "@hugeicons/react";

import { cn } from "@/lib/utils";

export type IconProps = SVGProps<SVGSVGElement> & {
  strokeWidth?: number;
};

export function Icon({
  icon,
  className,
  strokeWidth = 2,
  ...props
}: IconProps & { icon: IconSvgElement }) {
  return (
    <HugeiconsIcon
      icon={icon}
      strokeWidth={strokeWidth}
      className={cn("size-4 shrink-0", className)}
      {...props}
    />
  );
}

export function createIcon(icon: IconSvgElement): ComponentType<IconProps> {
  function CreatedIcon({ className, strokeWidth = 2, ...props }: IconProps) {
    return <Icon icon={icon} className={className} strokeWidth={strokeWidth} {...props} />;
  }

  CreatedIcon.displayName = "Hugeicon";
  return CreatedIcon;
}
