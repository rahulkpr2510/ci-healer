// frontend/src/components/ui/LanguageBadge.tsx

const LANG_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  Python: {
    bg: "bg-blue-50 dark:bg-blue-500/10",
    text: "text-blue-700 dark:text-blue-300",
    dot: "bg-blue-500",
  },
  JavaScript: {
    bg: "bg-yellow-50 dark:bg-yellow-500/10",
    text: "text-yellow-700 dark:text-yellow-300",
    dot: "bg-yellow-400",
  },
  TypeScript: {
    bg: "bg-sky-50 dark:bg-sky-500/10",
    text: "text-sky-700 dark:text-sky-300",
    dot: "bg-sky-500",
  },
  Go: {
    bg: "bg-teal-50 dark:bg-teal-500/10",
    text: "text-teal-700 dark:text-teal-300",
    dot: "bg-teal-400",
  },
  Java: {
    bg: "bg-orange-50 dark:bg-orange-500/10",
    text: "text-orange-700 dark:text-orange-300",
    dot: "bg-orange-500",
  },
  Ruby: {
    bg: "bg-red-50 dark:bg-red-500/10",
    text: "text-red-700 dark:text-red-300",
    dot: "bg-red-500",
  },
  Rust: {
    bg: "bg-amber-50 dark:bg-amber-500/10",
    text: "text-amber-700 dark:text-amber-300",
    dot: "bg-amber-500",
  },
  "C#": {
    bg: "bg-violet-50 dark:bg-violet-500/10",
    text: "text-violet-700 dark:text-violet-300",
    dot: "bg-violet-500",
  },
  C: {
    bg: "bg-zinc-100 dark:bg-zinc-800",
    text: "text-zinc-700 dark:text-zinc-300",
    dot: "bg-zinc-500",
  },
  "C++": {
    bg: "bg-indigo-50 dark:bg-indigo-500/10",
    text: "text-indigo-700 dark:text-indigo-300",
    dot: "bg-indigo-500",
  },
  PHP: {
    bg: "bg-purple-50 dark:bg-purple-500/10",
    text: "text-purple-700 dark:text-purple-300",
    dot: "bg-purple-500",
  },
  Kotlin: {
    bg: "bg-orange-50 dark:bg-orange-500/10",
    text: "text-orange-700 dark:text-orange-300",
    dot: "bg-orange-400",
  },
  Swift: {
    bg: "bg-orange-50 dark:bg-orange-500/10",
    text: "text-orange-700 dark:text-orange-300",
    dot: "bg-orange-500",
  },
  Scala: {
    bg: "bg-rose-50 dark:bg-rose-500/10",
    text: "text-rose-700 dark:text-rose-300",
    dot: "bg-rose-500",
  },
  Shell: {
    bg: "bg-zinc-100 dark:bg-zinc-800",
    text: "text-zinc-600 dark:text-zinc-400",
    dot: "bg-zinc-400",
  },
  Unknown: {
    bg: "bg-zinc-100 dark:bg-zinc-800",
    text: "text-zinc-500 dark:text-zinc-400",
    dot: "bg-zinc-400",
  },
};

const TIER_LABEL: Record<string, { label: string; cls: string }> = {
  full: {
    label: "Full Support",
    cls: "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20",
  },
  partial: {
    label: "LLM-Only",
    cls: "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/20",
  },
  none: {
    label: "Limited",
    cls: "text-zinc-500 dark:text-zinc-400 bg-zinc-100 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700",
  },
};

interface LanguageBadgeProps {
  language: string;
  tier?: "full" | "partial" | "none";
  size?: "sm" | "md";
}

export default function LanguageBadge({
  language,
  tier,
  size = "md",
}: LanguageBadgeProps) {
  const c = LANG_COLORS[language] ?? LANG_COLORS.Unknown;
  const t = tier ? TIER_LABEL[tier] : null;

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span
        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 ${size === "sm" ? "py-0.5 text-[10px]" : "py-1 text-xs"} font-semibold ${c.bg} ${c.text}`}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
        {language}
      </span>
      {t && (
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium border ${t.cls}`}
        >
          {t.label}
        </span>
      )}
    </div>
  );
}
