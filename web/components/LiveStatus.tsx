"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api, type HealthResponse } from "@/lib/api";

type Status =
  | { kind: "loading" }
  | { kind: "live"; health: HealthResponse }
  | { kind: "down" };

/**
 * Pings /health on mount. Three visible states:
 *   loading → amber dot, "checking backend"
 *   live    → green dot, "Live · N pages indexed"
 *   down    → amber dot, "Open source · in active development"
 *
 * Falling back to the in-development copy on failure means a backend outage
 * doesn't make the page look broken — it just reads as a project that
 * isn't live yet, which is the same as the static state.
 */
export function LiveStatus() {
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    api
      .health(controller.signal)
      .then((health) => setStatus({ kind: "live", health }))
      .catch(() => setStatus({ kind: "down" }));
    return () => controller.abort();
  }, []);

  let dot: React.ReactNode;
  let label: string;
  if (status.kind === "live") {
    dot = (
      <span className="relative flex h-1.5 w-1.5">
        <span className="absolute inset-0 rounded-full bg-emerald-400 animate-ping opacity-60" />
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
      </span>
    );
    const pages = status.health.indexed_pages.toLocaleString();
    label = `Live · ${pages} pages indexed`;
  } else if (status.kind === "down") {
    dot = <span className="h-1.5 w-1.5 rounded-full bg-amber-300" />;
    label = "Open source · in active development";
  } else {
    dot = <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-pulse" />;
    label = "Checking backend…";
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      className="inline-flex items-center gap-2 rounded-full glass px-3 py-1 text-xs text-slate-300/90"
    >
      {dot}
      <span>{label}</span>
    </motion.div>
  );
}
