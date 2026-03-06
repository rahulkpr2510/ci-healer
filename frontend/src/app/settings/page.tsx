// frontend/src/app/settings/page.tsx
"use client";

import { useRouter } from "next/navigation";
import {
  User,
  LogOut,
  Github,
  Calendar,
  Clock,
  Shield,
  CheckCircle2,
} from "lucide-react";
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

  const initials = user?.github_username
    ? user.github_username.slice(0, 2).toUpperCase()
    : "?";

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

      {/* Profile card — hero style */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
        {/* Cover gradient */}
        <div className="h-20 bg-gradient-to-r from-violet-600/20 via-violet-500/10 to-transparent" />
        <div className="px-5 pb-5 -mt-10">
          {/* Avatar with ring */}
          <div className="relative inline-block mb-3">
            {user?.github_avatar_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.github_avatar_url}
                alt={user.github_username}
                className="w-16 h-16 rounded-full border-4 border-zinc-900 shadow-lg"
              />
            ) : (
              <div className="w-16 h-16 rounded-full border-4 border-zinc-900 shadow-lg bg-violet-600 flex items-center justify-center">
                <span className="text-white font-bold text-lg">{initials}</span>
              </div>
            )}
            <div
              className="absolute bottom-0.5 right-0.5 w-4 h-4 rounded-full bg-emerald-500 border-2 border-zinc-900"
              title="Connected"
            />
          </div>

          <div className="flex items-end justify-between">
            <div>
              <h2 className="text-lg font-bold text-zinc-900 dark:text-white leading-tight">
                {user?.github_username ?? "—"}
              </h2>
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                {user?.github_email ?? "No email on record"}
              </p>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-emerald-500 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full">
              <CheckCircle2 size={11} />
              GitHub connected
            </div>
          </div>
        </div>
      </div>

      {/* Account details */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-zinc-100 dark:border-zinc-800">
          <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            Account Details
          </h2>
        </div>
        <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
          {[
            {
              icon: Github,
              label: "Username",
              value: user?.github_username ?? "—",
            },
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
              <div className="w-7 h-7 rounded-md bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center shrink-0">
                <Icon size={13} className="text-zinc-400 dark:text-zinc-500" />
              </div>
              <span className="text-sm text-zinc-500 dark:text-zinc-400 w-28 shrink-0">
                {label}
              </span>
              <span className="text-sm text-zinc-800 dark:text-zinc-200 font-medium truncate">
                {value}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Authentication info */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-lg bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center">
            <Github size={16} className="text-zinc-500" />
          </div>
          <div>
            <p className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
              GitHub OAuth
            </p>
            <p className="text-xs text-zinc-400 dark:text-zinc-500">
              Authentication method
            </p>
          </div>
          <div className="ml-auto flex items-center gap-1.5 text-xs text-emerald-500 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            Active
          </div>
        </div>
        <p className="text-xs text-zinc-400 dark:text-zinc-600 leading-relaxed">
          Your account is authenticated via GitHub OAuth 2.0. CI Healer only
          requests the repository permissions needed to run, clone, commit, and
          open pull requests on your behalf.
        </p>
      </div>

      {/* Sign out */}
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
              Sign out
            </p>
            <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-0.5">
              Ends your session on this device.
            </p>
          </div>
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
