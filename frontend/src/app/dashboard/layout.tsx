// frontend/src/app/dashboard/layout.tsx

import type { ReactNode } from "react";
import AppShell from "@/components/layout/AppShell";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
