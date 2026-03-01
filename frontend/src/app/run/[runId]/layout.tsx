// frontend/src/app/run/[runId]/layout.tsx

import type { ReactNode } from "react";
import AppShell from "@/components/layout/AppShell";

export default function RunLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
