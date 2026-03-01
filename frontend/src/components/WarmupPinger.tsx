// frontend/src/components/WarmupPinger.tsx
// Fires a single warmup ping on app load so both the backend and AI engine
// (separate Render services) start waking up before the user does anything.

"use client";

import { useEffect } from "react";
import { startupWarmup } from "@/lib/api";

export default function WarmupPinger() {
  useEffect(() => {
    startupWarmup();
  }, []);

  return null;
}
