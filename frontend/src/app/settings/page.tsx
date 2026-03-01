// frontend/src/app/settings/page.tsx
"use client";

import { useRouter } from "next/navigation";
import { User, LogOut, Github, Calendar, Clock, Shield } from "lucide-react";
import { logout } from "@/lib/api";
import { useAgentStore, selectUser } from "@/store/agentStore";

export default function SettingsPage() {
  const router = useRouter();
  const user = useAgentStore(selectUser);

  async function handleLogout() {
    try {
      await logout();
    } catch {
      // ignore
    }
    router.push("/auth/login");
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-zinc-900 dark:text-white">
          Settings
        </h1>
        <p className="text-sm text-zinc-500 mt-0.5">
          Manage your account and preferences.
        </p>
      </div>

      {/* Profile card */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-white">
            Profile
          </h2>
        </div>
        <div className="px-5 py-5 flex items-start gap-4">
          {/* Avatar */}
          <div className="shrink-0">
            {user?.github_avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.github_avatar_url}
                alt={user.github_username}
                className="w-14 h-14 rounded-full border-2 border-zinc-200 dark:border-zinc-700"
              />
            ) : (
              <div className="w-14 h-14 rounded-full bg-zinc-100 dark:bg-zinc-800 border-2 border-zinc-200 dark:border-zinc-700 flex items-center justify-center">
                <User size={24} className="text-zinc-400" />
              </div>
            )}
          </div>

          {/* Info */}
          <div className="min-w-0 flex-1">
            <p className="text-base font-bold text-zinc-900 dark:text-white">
              {user?.github_username ?? "—"}
            </p>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">
              {user?.github_email ?? "No email provided"}
            </p>
            <div className="flex items-center gap-1.5 mt-2 text-xs text-zinc-400 dark:text-zinc-500">
              <Github size={12} />
              <span>Connected via GitHub OAuth</span>
            </div>
          </div>
        </div>
      </div>

      {/* Account details */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-white">
            Account Details
          </h2>
        </div>
        <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
          {[
            {
              icon: Shield,
              label: "GitHub ID",
              value: user?.github_id ? `#${user.github_id}` : "—",
            },
            {
              icon: Calendar,
              label: "Member Since",
              value: user?.created_at
                ? new Date(user.created_at).toLocaleDateString(undefined, {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })
                : "—",
            },
            {
              icon: Clock,
              label: "Last Login",
              value: user?.last_login_at
                ? new Date(user.last_login_at).toLocaleString()
                : "—",
            },
          ].map(({ icon: Icon, label, value }) => (
            <div key={label} className="flex items-center gap-4 px-5 py-3.5">
              <Icon
                size={14}
                className="text-zinc-400 dark:text-zinc-600 shrink-0"
              />
              <span className="text-sm text-zinc-500 dark:text-zinc-400 w-32 shrink-0">
                {label}
              </span>
              <span className="text-sm text-zinc-800 dark:text-zinc-200 font-medium">
                {value}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Danger zone */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-white">
            Session
          </h2>
        </div>
        <div className="px-5 py-5">
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">
            Sign out of your CI Healer account on this device.
          </p>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-red-200 dark:border-red-500/30 text-red-600 dark:text-red-400 text-sm font-medium hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors"
          >
            <LogOut size={14} />
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}
