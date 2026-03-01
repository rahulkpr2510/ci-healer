// frontend/src/app/repos/layout.tsx
// frontend/src/app/analytics/layout.tsx
// frontend/src/app/settings/layout.tsx

import type { ReactNode } from "react";
import AppShell from "@/components/layout/AppShell";

export default function Layout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
