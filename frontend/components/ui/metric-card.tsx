import { clsx } from "clsx";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";
import type { ReactNode } from "react";
import { Sparkline } from "./sparkline";

export function MetricCard({
  label,
  value,
  unit,
  delta,
  trend,
  icon,
  spark,
  sparkColor = "#10b981",
}: {
  label: string;
  value: string | number;
  unit?: string;
  delta?: number; // positive/negative percent
  trend?: "up" | "down" | "flat";
  icon?: ReactNode;
  spark?: number[];
  sparkColor?: string;
}) {
  const deltaDirection = trend ?? (delta == null ? "flat" : delta > 0 ? "up" : delta < 0 ? "down" : "flat");
  const deltaColor =
    deltaDirection === "up"
      ? "text-emerald-400"
      : deltaDirection === "down"
      ? "text-rose-400"
      : "text-zinc-400";
  const DeltaIcon = deltaDirection === "up" ? ArrowUpRight : deltaDirection === "down" ? ArrowDownRight : Minus;

  return (
    <div className="group relative overflow-hidden rounded-xl border border-white/[0.06] bg-surface/80 px-5 py-4 shadow-glow card-lift">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2 text-2xs uppercase tracking-wider text-subtle">
          {icon ? <span className="text-zinc-500">{icon}</span> : null}
          <span>{label}</span>
        </div>
        {delta != null ? (
          <span className={clsx("inline-flex items-center gap-0.5 text-2xs font-medium", deltaColor)}>
            <DeltaIcon className="h-3 w-3" />
            {Math.abs(delta).toFixed(1)}%
          </span>
        ) : null}
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className="text-2xl font-semibold tabular-nums text-zinc-50">{value}</span>
        {unit ? <span className="text-xs text-subtle">{unit}</span> : null}
      </div>
      {spark && spark.length > 1 ? (
        <div className="mt-2 -mx-1">
          <Sparkline data={spark} color={sparkColor} height={32} />
        </div>
      ) : null}
    </div>
  );
}
