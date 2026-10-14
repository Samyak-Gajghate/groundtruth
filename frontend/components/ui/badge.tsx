import { clsx } from "clsx";
import type { ReactNode } from "react";

type Variant = "default" | "success" | "info" | "warning" | "danger" | "violet" | "neutral";

const styles: Record<Variant, string> = {
  default: "bg-white/5 text-zinc-300 ring-1 ring-inset ring-white/10",
  neutral: "bg-zinc-800/60 text-zinc-300 ring-1 ring-inset ring-white/10",
  success: "bg-emerald-500/10 text-emerald-300 ring-1 ring-inset ring-emerald-500/20",
  info: "bg-sky-500/10 text-sky-300 ring-1 ring-inset ring-sky-500/20",
  warning: "bg-amber-500/10 text-amber-300 ring-1 ring-inset ring-amber-500/20",
  danger: "bg-rose-500/10 text-rose-300 ring-1 ring-inset ring-rose-500/20",
  violet: "bg-violet-500/10 text-violet-300 ring-1 ring-inset ring-violet-500/20",
};

export function Badge({
  variant = "default",
  children,
  dot = false,
  className,
}: {
  variant?: Variant;
  children: ReactNode;
  dot?: boolean;
  className?: string;
}) {
  return (
    <span className={clsx(
      "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-2xs font-medium",
      styles[variant],
      className,
    )}>
      {dot ? <span className={clsx("h-1.5 w-1.5 rounded-full", dotColor(variant))} /> : null}
      {children}
    </span>
  );
}

function dotColor(v: Variant): string {
  switch (v) {
    case "success": return "bg-emerald-400";
    case "info": return "bg-sky-400";
    case "warning": return "bg-amber-400";
    case "danger": return "bg-rose-400";
    case "violet": return "bg-violet-400";
    default: return "bg-zinc-400";
  }
}
