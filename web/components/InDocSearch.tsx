"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search as SearchIcon, X, Loader2 } from "lucide-react";
import { api, type SearchHit, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

export function InDocSearch({
  source,
  sourceId,
  pageCount,
  onJumpToPage,
  currentPage,
}: {
  source: string;
  sourceId: string;
  pageCount: number;
  onJumpToPage: (pageNumber: number) => void;
  currentPage?: number;
}) {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 250);
    return () => clearTimeout(t);
  }, [query]);

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
        limit: Math.min(pageCount, 20),
        source,
        sourceId,
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
  }, [debounced, source, sourceId, pageCount]);

  return (
    <div className="rounded-2xl glass ring-glow p-4">
      <div className="text-[10px] uppercase tracking-[0.25em] text-slate-500 mb-3">
        Search inside this document
      </div>

      <div className="relative">
        <div className="flex items-center rounded-xl glass-strong ring-1 ring-white/10 focus-within:ring-violet-400/40 transition-all">
          <SearchIcon className="ml-3.5 h-3.5 w-3.5 text-slate-500" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. royalty, mineral interest, signature page"
            className="flex-1 bg-transparent px-3 py-2.5 text-[13px] text-white placeholder:text-slate-500 outline-none"
            aria-label="Search in document"
          />
          {query ? (
            <button
              onClick={() => setQuery("")}
              aria-label="Clear"
              className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded text-slate-500 hover:text-white hover:bg-white/5 transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          ) : null}
          {loading ? (
            <Loader2 className="mr-3 h-3.5 w-3.5 animate-spin text-cyan-300" />
          ) : null}
        </div>
      </div>

      {/* Results */}
      <AnimatePresence mode="wait">
        {error ? (
          <motion.div
            key="err"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mt-3 rounded-lg border border-rose-500/30 bg-rose-500/5 p-2 text-[11px] text-rose-200 font-mono"
          >
            {error}
          </motion.div>
        ) : !debounced ? null : hits && hits.length === 0 ? (
          <motion.div
            key="none"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mt-3 text-[11px] text-slate-500"
          >
            No matching pages.
          </motion.div>
        ) : hits && hits.length > 0 ? (
          <motion.div
            key="hits"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mt-3 space-y-2 max-h-[420px] overflow-y-auto pr-1"
          >
            {hits.map((hit, i) => {
              const displayPage = hit.page_number + 1;
              const isCurrent = currentPage === displayPage;
              return (
                <button
                  key={`${hit.page_number}-${i}`}
                  onClick={() => onJumpToPage(displayPage)}
                  className={cn(
                    "group w-full text-left rounded-lg px-3 py-2.5 transition-all",
                    isCurrent
                      ? "bg-violet-500/15 ring-1 ring-violet-400/30"
                      : "hover:bg-white/5 ring-1 ring-transparent",
                  )}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="font-mono text-[11px] text-cyan-300">
                        page {displayPage}
                      </span>
                      {isCurrent ? (
                        <span className="text-[9px] uppercase tracking-[0.2em] text-violet-300">
                          viewing
                        </span>
                      ) : null}
                    </span>
                    <span className="font-mono text-[10px] text-slate-500">
                      {hit.score.toFixed(2)}
                    </span>
                  </div>
                  {hit.snippet ? (
                    <p className="text-[12px] leading-relaxed text-slate-200/90 whitespace-pre-wrap break-words">
                      <Highlighted text={hit.snippet} query={debounced} />
                    </p>
                  ) : (
                    <p className="text-[10px] italic text-slate-500">
                      No text preview (scanned page) — click to view.
                    </p>
                  )}
                </button>
              );
            })}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

function Highlighted({ text, query }: { text: string; query: string }) {
  if (!text || !query) return <>{text}</>;
  const words = query.split(/\s+/).filter((w) => w.length > 2);
  if (!words.length) return <>{text}</>;
  const escaped = words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const splitter = new RegExp(`(${escaped.join("|")})`, "gi");
  const wordSet = new Set(words.map((w) => w.toLowerCase()));
  const parts = text.split(splitter);
  return (
    <>
      {parts.map((part, i) =>
        wordSet.has(part.toLowerCase()) ? (
          <mark
            key={i}
            className="rounded bg-violet-400/30 text-white px-0.5"
          >
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}
