// frontend/src/components/run/AgentErrorsPanel.tsx

import { AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

interface AgentErrorsPanelProps {
  errors: string[];
}

export default function AgentErrorsPanel({ errors }: AgentErrorsPanelProps) {
  const [expanded, setExpanded] = useState(false);

  if (!errors.length) return null;

  const preview = errors.slice(0, 2);
  const rest = errors.slice(2);

  return (
    <div className="bg-amber-50 dark:bg-amber-500/5 border border-amber-200 dark:border-amber-500/20 rounded-xl overflow-hidden">
      <div className="flex items-center gap-2.5 px-4 py-3">
        <AlertTriangle
          size={14}
          className="text-amber-600 dark:text-amber-400 shrink-0"
        />
        <span className="text-xs font-semibold text-amber-700 dark:text-amber-300 flex-1">
          {errors.length} tool warning{errors.length !== 1 ? "s" : ""} during
          run
        </span>
        {rest.length > 0 && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-200 transition-colors"
          >
            {expanded ? (
              <>
                Show less <ChevronUp size={12} />
              </>
            ) : (
              <>
                +{rest.length} more <ChevronDown size={12} />
              </>
            )}
          </button>
        )}
      </div>
      <div className="px-4 pb-3 space-y-1.5">
        {(expanded ? errors : preview).map((err, i) => (
          <p
            key={i}
            className="text-[11px] font-mono text-amber-700 dark:text-amber-300/80 leading-relaxed bg-amber-100/50 dark:bg-amber-500/10 rounded px-2 py-1"
          >
            ⚠ {err}
          </p>
        ))}
      </div>
    </div>
  );
}
