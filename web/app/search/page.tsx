"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { Search as SearchIcon, X, Loader2, ArrowUpRight } from "lucide-react";
import { api, type SearchHit, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

type Filter = "all" | "tx_glo" | "sec_edgar";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "All sources" },
  { value: "tx_glo", label: "Texas GLO" },
  { value: "sec_edgar", label: "SEC EDGAR" },
];

const SUGGESTIONS = [
  "Dallas County mineral grant",
  "oil and gas lease",
  "Horton Family Trust",
  "Reeves County",
] as const;

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Debounce the query so we're not firing /search on every keystroke.
  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 250);
    return () => clearTimeout(t);
  }, [query]);

  // Run the search whenever the debounced query or filter changes.
  useEffect(() => {
    if (!debounced) {
      setHits(null);
      setError(null);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    api
      .search(debounced, {
        limit: 24,
        source: filter === "all" ? undefined : filter,
        signal: controller.signal,
      })
      .then((res) => setHits(res.hits))
      .catch((err) => {
        if (controller.signal.aborted) return;
        if (err instanceof ApiError) {
          setError(`backend ${err.status}: ${err.message}`);
        } else {
          setError("couldn't reach the backend");
        }
        setHits([]);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [debounced, filter]);

  // Focus the input on mount.
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <main className="relative min-h-screen pt-32 pb-24">
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="text-xs uppercase tracking-[0.3em] text-cyan-300/80">
            Search
          </div>
          <h1 className="mt-3 text-[clamp(2rem,5vw,3.5rem)] font-semibold tracking-[-0.03em] leading-tight text-gradient">
            Visual late-interaction search.
          </h1>
          <p className="mt-3 max-w-2xl text-sm sm:text-base text-slate-300/80 leading-relaxed">
            Queries hit the live Modal backend. Rankings are mock-hashed in
            this build; semantic ColQwen2 rankings activate after the GPU
            indexing run.
          </p>
        </motion.div>

        {/* Search input */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="mt-10"
        >
          <div className="relative group">
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-violet-500/20 via-cyan-400/20 to-violet-500/20 blur-xl opacity-0 group-focus-within:opacity-100 transition-opacity duration-500 -z-10" />
            <div className="relative flex items-center rounded-2xl glass-strong ring-1 ring-white/10 focus-within:ring-violet-400/40 transition-all">
              <SearchIcon className="ml-5 h-4.5 w-4.5 text-slate-400" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search the indexed corpus…"
                className="flex-1 bg-transparent px-4 py-4 text-base text-white placeholder:text-slate-500 outline-none"
                aria-label="Search query"
              />
              {query ? (
                <button
                  onClick={() => setQuery("")}
                  aria-label="Clear"
                  className="mr-3 inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              ) : null}
              {loading ? (
                <Loader2 className="mr-5 h-4 w-4 animate-spin text-cyan-300" />
              ) : null}
            </div>
          </div>

          {/* Filter pills */}
          <div className="mt-5 flex flex-wrap items-center gap-2">
            {FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => setFilter(f.value)}
                className={cn(
                  "rounded-full px-3.5 py-1.5 text-xs font-medium transition-all",
                  filter === f.value
                    ? "bg-gradient-to-r from-violet-500/90 to-cyan-500/90 text-white shadow-glow ring-1 ring-white/10"
                    : "glass text-slate-300 hover:text-white hover-glow",
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Body */}
        <div className="mt-14">
          <AnimatePresence mode="wait">
            {!debounced ? (
              <EmptyState onPick={(q) => setQuery(q)} key="empty" />
            ) : error ? (
              <ErrorState message={error} key="error" />
            ) : hits === null ? null : hits.length === 0 ? (
              <NoResults query={debounced} key="no-results" />
            ) : (
              <ResultsGrid hits={hits} key="results" />
            )}
          </AnimatePresence>
        </div>
      </div>
    </main>
  );
}

function ResultsGrid({ hits }: { hits: SearchHit[] }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="mb-4 text-xs text-slate-500 font-mono">
        {hits.length} result{hits.length === 1 ? "" : "s"}
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {hits.map((hit, i) => (
          <ResultCard key={`${hit.source}/${hit.source_id}/${hit.page_number}`} hit={hit} delay={i * 0.04} />
        ))}
      </div>
    </motion.div>
  );
}

function ResultCard({ hit, delay }: { hit: SearchHit; delay: number }) {
  const sourceLabel =
    hit.source === "tx_glo"
      ? "Texas GLO"
      : hit.source === "sec_edgar"
        ? "SEC EDGAR"
        : hit.source;
  const sourceTint =
    hit.source === "tx_glo"
      ? "text-violet-300 bg-violet-400/10"
      : hit.source === "sec_edgar"
        ? "text-cyan-300 bg-cyan-400/10"
        : "text-slate-300 bg-slate-400/10";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      <Link
        href={`/documents/${encodeURIComponent(hit.source)}/${encodeURIComponent(hit.source_id)}`}
        className="group block rounded-2xl glass ring-glow p-5 hover-glow hover:-translate-y-0.5 transition-all duration-300"
      >
        <div className="flex items-start justify-between gap-3">
          <span
            className={cn(
              "inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-medium",
              sourceTint,
            )}
          >
            {sourceLabel}
          </span>
          <span className="font-mono text-[11px] text-slate-500">
            {hit.score.toFixed(3)}
          </span>
        </div>
        <h3 className="mt-3 text-sm font-medium text-white leading-snug line-clamp-2">
          {hit.title || `${hit.source} / ${hit.source_id}`}
        </h3>
        <div className="mt-3 flex items-center justify-between text-[11px]">
          <span className="font-mono text-slate-500">
            {hit.source_id} · p{hit.page_number}
          </span>
          <ArrowUpRight className="h-3.5 w-3.5 text-slate-500 group-hover:text-cyan-300 transition-colors" />
        </div>
      </Link>
    </motion.div>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="text-sm text-slate-400"
    >
      <p className="mb-4">Try one of these to get started:</p>
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="rounded-full glass px-3.5 py-1.5 text-xs text-slate-300 hover:text-white hover-glow transition-all"
          >
            {s}
          </button>
        ))}
      </div>
    </motion.div>
  );
}

function NoResults({ query }: { query: string }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl glass p-8 text-center"
    >
      <p className="text-sm text-slate-400">
        No hits for{" "}
        <span className="font-mono text-slate-300">&ldquo;{query}&rdquo;</span>
      </p>
    </motion.div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl glass border border-rose-500/30 p-6 text-sm text-rose-200"
    >
      <div className="font-medium mb-1">Search failed</div>
      <div className="font-mono text-xs text-rose-300/80">{message}</div>
    </motion.div>
  );
}
