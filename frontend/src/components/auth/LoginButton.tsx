// frontend/src/components/auth/LoginButton.tsx

"use client";

import { Github } from "lucide-react";
import { getGithubLoginUrl } from "@/lib/api";

export default function LoginButton() {
  return (
    <a
      href={getGithubLoginUrl()}
      className="w-full inline-flex items-center justify-center gap-2.5 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 px-5 py-2.5 text-sm font-semibold hover:bg-zinc-800 dark:hover:bg-zinc-100 transition-colors shadow-sm"
    >
      <Github size={16} />
      Continue with GitHub
    </a>
  );
}
