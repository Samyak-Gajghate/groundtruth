import { clsx } from "clsx";
import type { ReactNode, HTMLAttributes } from "react";

export function Card({
  className,
  hoverable = false,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement> & { hoverable?: boolean; children: ReactNode }) {
  return (
    <div
      className={clsx(
        "rounded-xl bg-surface/80 backdrop-blur-sm",
        "border border-white/[0.06]",
        "shadow-glow",
        hoverable && "card-lift",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between px-5 pt-5 pb-3">
      <div>
        <h3 className="text-sm font-medium text-zinc-100">{title}</h3>
        {subtitle ? <p className="text-2xs text-subtle mt-0.5">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function CardBody({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("px-5 pb-5", className)}>{children}</div>;
}
