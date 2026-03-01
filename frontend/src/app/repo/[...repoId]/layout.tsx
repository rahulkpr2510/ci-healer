// frontend/src/app/repo/[...repoId]/layout.tsx
import AppShell from "@/components/layout/AppShell";

export default function RepoLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell>{children}</AppShell>;
}
