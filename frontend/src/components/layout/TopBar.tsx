// frontend/src/components/layout/TopBar.tsx

"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { LogOut, User as UserIcon } from "lucide-react";

import { logout } from "@/lib/api";
import { useAgentStore } from "@/store/agentStore";

export default function TopBar() {
  const user = useAgentStore((s) => s.user);
  const setUser = useAgentStore((s) => s.setUser);
  const router = useRouter();

  async function handleLogout() {
    await logout();
    setUser(null);
    router.push("/auth/login");
  }

  return (
    <header className="h-[57px] border-b border-zinc-200 dark:border-zinc-800/60 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md px-4 flex items-center justify-end gap-2">
      {!user ? (
        <div className="text-xs text-zinc-400">Not signed in</div>
      ) : (
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-2 py-1 rounded-lg text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          title="Sign out"
        >
          {user.github_avatar_url ? (
            <Image
              src={user.github_avatar_url}
              alt={user.github_username}
              width={24}
              height={24}
              className="rounded-full ring-1 ring-zinc-200 dark:ring-zinc-700"
            />
          ) : (
            <div className="w-6 h-6 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center">
              <UserIcon size={12} className="text-zinc-500" />
            </div>
          )}
          <span className="text-sm font-medium hidden sm:block">
            {user.github_username}
          </span>
          <LogOut size={13} className="ml-0.5" />
        </button>
      )}
    </header>
  );
}
