// frontend/src/components/run/AgentErrorsPanel.tsx

import { AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

interface AgentErrorsPanelProps {
  errors: string[];
}

export default function AgentErrorsPanel({ errors }: AgentErrorsPanelProps) {
  const [expanded, setExpanded] = useState(false);

  if (!errors.length) return null;

  return (
    <div className="bg-amber-50 dark:bg-amber-500/5 border border-amber-200 dark:border-amber-500/20 rounded-xl overflow-hidden">
      {/* Accordion header — always visible */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-2.5 px-4 py-3 hover:bg-amber-100/40 dark:hover:bg-amber-500/10 transition-colors text-left"
      >
        <AlertTriangle
          size={14}
          className="text-amber-600 dark:text-amber-400 shrink-0"
        />
        <span className="text-xs font-semibold text-amber-700 dark:text-amber-300 flex-1">
          Agent warnings
        </span>
        <span className="text-[10px] font-bold bg-amber-200 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300 px-1.5 py-0.5 rounded-full tabular-nums">
          {errors.length}
        </span>
        {expanded ? (
          <ChevronUp size={13} className="text-amber-500 shrink-0" />
        ) : (
          <ChevronDown size={13} className="text-amber-500 shrink-0" />
        )}
      </button>

      {/* Collapsible body */}
      {expanded && (
        <div className="px-4 pb-3 space-y-1.5 border-t border-amber-200/60 dark:border-amber-500/15 pt-2">
          {errors.map((err, i) => (
            <p
              key={i}
              className="text-[11px] font-mono text-amber-700 dark:text-amber-300/80 leading-relaxed bg-amber-100/50 dark:bg-amber-500/10 rounded px-2 py-1"
            >
              <span className="text-amber-500 mr-1 select-none">
                {String(i + 1).padStart(2, "0")}.
              </span>
              {err}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
