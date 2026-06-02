import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function TypographyH3({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <h3 className={cn("scroll-m-20 text-lg font-semibold tracking-tight", className)}>
      {children}
    </h3>
  );
}

export function TypographyP({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn("leading-7 [&:not(:first-child)]:mt-3", className)}>{children}</p>;
}

export function TypographyList({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <ul className={cn("my-3 ml-6 list-disc [&>li]:mt-1", className)}>{children}</ul>;
}

export function TypographyMuted({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <p className={cn("text-sm text-muted-foreground", className)}>{children}</p>;
}
