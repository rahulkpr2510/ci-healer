// frontend/src/app/page.tsx

import type { Metadata } from "next";
import Link from "next/link";
import {
  GitBranch,
  Zap,
  BarChart3,
  Terminal,
  CheckCircle2,
  ArrowRight,
  Github,
  Bot,
  Wrench,
  Globe,
  GitPullRequest,
} from "lucide-react";

export const metadata: Metadata = {
  title: "CI Healer — AI-Powered CI/CD Auto-Fixer",
  description:
    "Connect your GitHub repository and let our AI agent automatically diagnose failing tests, generate fixes, and open a pull request.",
};

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-zinc-100 dark:border-zinc-900 bg-white/90 dark:bg-zinc-950/90 backdrop-blur-md">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-600 to-violet-800 flex items-center justify-center shadow-sm shadow-violet-500/30">
              <Zap size={13} className="text-white" />
            </div>
            <span className="font-semibold text-zinc-900 dark:text-white text-sm">
              CI Healer
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/auth/login"
              className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 text-sm font-medium hover:bg-zinc-800 dark:hover:bg-zinc-100 transition-colors"
            >
              <Github size={14} />
              Sign in
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-32 pb-24 px-6 overflow-hidden">
        <div className="absolute inset-0 dot-grid" />
        <div className="absolute top-24 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-violet-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-50 dark:bg-violet-500/10 border border-violet-200 dark:border-violet-500/20 text-violet-600 dark:text-violet-400 text-xs font-medium mb-7">
            <Zap size={11} />
            AI-powered CI/CD healing
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-zinc-900 dark:text-white leading-[1.1] mb-5">
            Your CI pipeline.
            <br />
            <span className="text-zinc-400 dark:text-zinc-500">
              Fixed automatically.
            </span>
          </h1>

          <p className="text-base sm:text-lg text-zinc-500 dark:text-zinc-400 max-w-xl mx-auto mb-10 leading-relaxed">
            Connect your GitHub repo and let our AI agent diagnose failing
            tests, generate minimal fixes, and open a pull request — zero manual
            work.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/auth/login"
              className="flex items-center gap-2 px-6 py-3 rounded-xl bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 font-semibold text-sm hover:bg-zinc-800 dark:hover:bg-zinc-100 transition-all shadow-sm hover:shadow"
            >
              <Github size={16} />
              Get started free
              <ArrowRight size={14} />
            </Link>
            <Link
              href="/dashboard"
              className="flex items-center gap-2 px-6 py-3 rounded-xl border border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-300 font-medium text-sm hover:bg-zinc-50 dark:hover:bg-zinc-900 transition-colors"
            >
              View dashboard
            </Link>
          </div>

          {/* Terminal preview */}
          <div className="mt-16 max-w-xl mx-auto">
            <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 overflow-hidden shadow-lg dark:shadow-none">
              <div className="flex items-center gap-1.5 px-4 py-2.5 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950/50">
                <div className="w-2.5 h-2.5 rounded-full bg-red-400/70" />
                <div className="w-2.5 h-2.5 rounded-full bg-amber-400/70" />
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-400/70" />
                <span className="ml-2 text-xs text-zinc-400 dark:text-zinc-600 font-mono">
                  ci-healer-agent
                </span>
              </div>
              <div className="p-4 space-y-1.5 log-line">
                {[
                  {
                    tag: "REPO_CLONED",
                    color: "text-emerald-600 dark:text-emerald-400",
                    text: "github.com/user/project",
                  },
                  {
                    tag: "TEST_DISCOVERED",
                    color: "text-zinc-500 dark:text-zinc-400",
                    text: "Found 24 test files",
                  },
                  {
                    tag: "TEST_FAILED",
                    color: "text-amber-600 dark:text-amber-400",
                    text: "3 failures detected",
                  },
                  {
                    tag: "FIX_GENERATED",
                    color: "text-violet-600 dark:text-violet-400",
                    text: "auth.py:42  [LINTING]",
                  },
                  {
                    tag: "FIX_GENERATED",
                    color: "text-violet-600 dark:text-violet-400",
                    text: "utils.py:18  [SYNTAX]",
                  },
                  {
                    tag: "COMMIT_CREATED",
                    color: "text-zinc-500 dark:text-zinc-400",
                    text: "3 commits pushed",
                  },
                  {
                    tag: "RUN_COMPLETED",
                    color: "text-emerald-600 dark:text-emerald-400",
                    text: "All checks passing ✓",
                  },
                ].map(({ tag, color, text }) => (
                  <div
                    key={tag + text}
                    className="flex items-baseline gap-2 font-mono text-xs"
                  >
                    <CheckCircle2
                      size={11}
                      className="text-emerald-500 shrink-0 mt-0.5"
                    />
                    <span className={`font-semibold ${color}`}>[{tag}]</span>
                    <span className="text-zinc-500 dark:text-zinc-500">
                      {text}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 px-6 border-t border-zinc-100 dark:border-zinc-900">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-2xl font-bold text-zinc-900 dark:text-white mb-3">
              How it works
            </h2>
            <p className="text-zinc-500 dark:text-zinc-400 max-w-md mx-auto text-sm">
              Three steps from broken CI to a passing pull request
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                step: "01",
                icon: Github,
                title: "Connect Repository",
                description:
                  "Sign in with GitHub. Any repository with a failing CI pipeline is ready to heal.",
              },
              {
                step: "02",
                icon: Bot,
                title: "AI Diagnoses & Fixes",
                description:
                  "The agent clones, runs tests, classifies errors, and generates targeted fixes using LLMs and static analysers.",
              },
              {
                step: "03",
                icon: GitBranch,
                title: "PR Opened, CI Passes",
                description:
                  "Commits are pushed to a new auto-named branch and a pull request is opened automatically.",
              },
            ].map(({ step, icon: Icon, title, description }) => (
              <div
                key={step}
                className="relative p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors"
              >
                <span className="absolute -top-3 left-5 px-1.5 text-[10px] font-mono font-semibold bg-white dark:bg-zinc-950 text-zinc-400 dark:text-zinc-600 border border-zinc-200 dark:border-zinc-800 rounded">
                  {step}
                </span>
                <div className="w-9 h-9 rounded-lg bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 flex items-center justify-center mb-4">
                  <Icon
                    size={18}
                    className="text-zinc-600 dark:text-zinc-300"
                  />
                </div>
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-white mb-2">
                  {title}
                </h3>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                  {description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-6 border-t border-zinc-100 dark:border-zinc-900">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-2xl font-bold text-zinc-900 dark:text-white mb-3">
              Built for developers
            </h2>
            <p className="text-zinc-500 dark:text-zinc-400 max-w-md mx-auto text-sm">
              Everything you need to fix CI failures automatically
            </p>
          </div>

          <div className="grid sm:grid-cols-2 gap-5">
            {[
              {
                icon: Zap,
                title: "AI-Powered Fixes",
                description:
                  "LLMs generate minimal, targeted patches for linting, syntax, type, and logic errors — with iterative CI verification.",
              },
              {
                icon: Globe,
                title: "Multi-Language Support",
                description:
                  "Handles Python, JavaScript, TypeScript, Java, Go, HTML/CSS repos. Automatically detects language stack and runs appropriate analysers.",
              },
              {
                icon: GitPullRequest,
                title: "Automatic Pull Requests",
                description:
                  "Every run opens a PR with a clean diff. Branch names follow the pattern CI_HEALER_AI_FIX_N or your custom prefix.",
              },
              {
                icon: Terminal,
                title: "Live SSE Streaming",
                description:
                  "Watch the agent work in real time — every clone, test run, fix, and commit streamed to your browser as it happens.",
              },
              {
                icon: BarChart3,
                title: "Analytics Dashboard",
                description:
                  "Track pass rates, fix counts, and run history across all your repositories. Identify recurring failure patterns over time.",
              },
              {
                icon: Wrench,
                title: "Static Analysers",
                description:
                  "Runs ESLint, Pylint, mypy, flake8, and other language-specific tools to catch issues before and after each fix attempt.",
              },
            ].map(({ icon: Icon, title, description }) => (
              <div
                key={title}
                className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/30 hover:bg-zinc-50 dark:hover:bg-zinc-900/60 transition-colors"
              >
                <div className="w-9 h-9 rounded-lg bg-violet-50 dark:bg-violet-500/10 border border-violet-100 dark:border-violet-500/20 flex items-center justify-center mb-4">
                  <Icon
                    size={17}
                    className="text-violet-600 dark:text-violet-400"
                  />
                </div>
                <h3 className="text-sm font-semibold text-zinc-900 dark:text-white mb-1.5">
                  {title}
                </h3>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                  {description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6 border-t border-zinc-100 dark:border-zinc-900">
        <div className="max-w-lg mx-auto text-center">
          <div className="w-12 h-12 rounded-2xl bg-violet-100 dark:bg-violet-500/10 border border-violet-200 dark:border-violet-500/20 flex items-center justify-center mx-auto mb-5">
            <Zap size={22} className="text-violet-600 dark:text-violet-400" />
          </div>
          <h2 className="text-2xl font-bold text-zinc-900 dark:text-white mb-3">
            Ready to fix your CI?
          </h2>
          <p className="text-zinc-500 dark:text-zinc-400 text-sm mb-8">
            Connect your GitHub account and start healing pipelines in seconds.
          </p>
          <Link
            href="/auth/login"
            className="inline-flex items-center gap-2 px-7 py-3 rounded-xl bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 font-semibold text-sm hover:bg-zinc-800 dark:hover:bg-zinc-100 transition-all shadow-sm"
          >
            <Github size={16} />
            Get started with GitHub
            <ArrowRight size={14} />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-7 px-6 border-t border-zinc-100 dark:border-zinc-900">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-zinc-400 dark:text-zinc-600">
          <div className="flex items-center gap-2">
            <Zap size={13} className="text-violet-500" />
            <span className="font-medium text-zinc-600 dark:text-zinc-400">
              CI Healer
            </span>
          </div>
          <span>Autonomous CI/CD AI DevOps Agent</span>
        </div>
      </footer>
    </div>
  );
}
