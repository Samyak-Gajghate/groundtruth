"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Datum = Record<string, string | number>;

export function CostAreaChart({
  data,
  xKey,
  series,
  height = 220,
}: {
  data: Datum[];
  xKey: string;
  series: { key: string; color: string; label: string }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <defs>
          {series.map((s) => (
            <linearGradient key={s.key} id={`g-${s.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s.color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={s.color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
        <XAxis
          dataKey={xKey}
          stroke="#71717a"
          fontSize={11}
          tickLine={false}
          axisLine={false}
          tickMargin={8}
        />
        <YAxis
          stroke="#71717a"
          fontSize={11}
          tickLine={false}
          axisLine={false}
          tickMargin={4}
          width={48}
        />
        <Tooltip
          contentStyle={{
            background: "#0e0e12",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 8,
            fontSize: 12,
            color: "#fafafa",
          }}
          cursor={{ stroke: "rgba(255,255,255,0.12)", strokeWidth: 1 }}
        />
        {series.map((s) => (
          <Area
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.label}
            stroke={s.color}
            strokeWidth={2}
            fill={`url(#g-${s.key})`}
            isAnimationActive={false}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
