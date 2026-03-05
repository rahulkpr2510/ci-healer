// frontend/src/components/ui/StatCard.tsx

"use client";

import { useEffect, useRef, useState } from "react";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  sub?: string;
  accent?: "default" | "green" | "red" | "amber";
  trend?: "up" | "down" | null;
}

const ACCENT: Record<NonNullable<StatCardProps["accent"]>, string> = {
  default:
    "bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border-zinc-200 dark:border-zinc-700",
  green:
    "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/20",
  red: "bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 border-red-200 dark:border-red-500/20",
  amber:
    "bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-500/20",
};

function useCountUp(target: number, duration = 800): number {
  const [count, setCount] = useState(0);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    if (typeof target !== "number" || isNaN(target)) {
      setCount(target);
      return;
    }
    const start = performance.now();
    const animate = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(Math.round(eased * target));
      if (progress < 1) raf.current = requestAnimationFrame(animate);
    };
    raf.current = requestAnimationFrame(animate);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [target, duration]);

  return count;
}

export default function StatCard({
  label,
  value,
  icon: Icon,
  sub,
  accent = "default",
}: StatCardProps) {
  const numericValue =
    typeof value === "number" ? value : parseInt(String(value), 10);
  const isNumeric = !isNaN(numericValue) && typeof value === "number";
  const animated = useCountUp(isNumeric ? numericValue : 0);

  return (
    <div className="group bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 flex items-start gap-4 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors">
      <div
        className={`w-9 h-9 rounded-lg border flex items-center justify-center shrink-0 ${ACCENT[accent]}`}
      >
        <Icon size={16} />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-zinc-500 dark:text-zinc-500 font-medium">
          {label}
        </p>
        <p className="text-2xl font-bold text-zinc-900 dark:text-white mt-0.5 tabular-nums">
          {isNumeric ? animated : value}
        </p>
        {sub && (
          <p className="text-xs text-zinc-400 dark:text-zinc-600 mt-0.5 truncate">
            {sub}
          </p>
        )}
      </div>
    </div>
  );
}
