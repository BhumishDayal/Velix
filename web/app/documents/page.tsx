"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowUpRight, Loader2 } from "lucide-react";
import { api, type DocumentSummary, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

type Filter = "all" | "tx_glo" | "sec_edgar";
const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "All sources" },
  { value: "tx_glo", label: "Texas GLO" },
  { value: "sec_edgar", label: "SEC EDGAR" },
];

const PAGE_SIZE = 24;

export default function DocumentsPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const [offset, setOffset] = useState(0);
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setOffset(0);
  }, [filter]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    api
      .listDocuments({
        offset,
        limit: PAGE_SIZE,
        source: filter === "all" ? undefined : filter,
        signal: controller.signal,
      })
      .then((res) => {
        setDocs(res.documents);
        setTotal(res.total);
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        if (err instanceof ApiError) {
          setError(`backend ${err.status}: ${err.message}`);
        } else {
          setError("couldn't reach the backend");
        }
        setDocs([]);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [filter, offset]);

  return (
    <main className="relative min-h-screen pt-32 pb-24">
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="text-xs uppercase tracking-[0.3em] text-cyan-300/80">
            Documents
          </div>
          <h1 className="mt-3 text-[clamp(2rem,5vw,3.5rem)] font-semibold tracking-[-0.03em] leading-tight text-gradient">
            Browse the indexed corpus.
          </h1>
          <p className="mt-3 max-w-2xl text-sm sm:text-base text-slate-300/80 leading-relaxed">
            Public oil &amp; gas documents from SEC EDGAR and the Texas
            General Land Office. Click into any record to see the per-page
            metadata.
          </p>
        </motion.div>

        <div className="mt-8 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-2">
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
          <div className="text-xs font-mono text-slate-500">
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-cyan-300" />
            ) : (
              <>
                {total} total · showing {offset + 1}-
                {Math.min(offset + PAGE_SIZE, total)}
              </>
            )}
          </div>
        </div>

        {error ? (
          <div className="mt-10 rounded-2xl glass border border-rose-500/30 p-6 text-sm text-rose-200">
            <div className="font-medium mb-1">Failed to load documents</div>
            <div className="font-mono text-xs text-rose-300/80">{error}</div>
          </div>
        ) : (
          <>
            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              {docs.map((doc, i) => (
                <DocumentCard
                  key={`${doc.source}/${doc.source_id}`}
                  doc={doc}
                  delay={i * 0.03}
                />
              ))}
            </div>

            {docs.length === 0 && !loading ? (
              <div className="mt-10 rounded-2xl glass p-8 text-center text-sm text-slate-400">
                No documents.
              </div>
            ) : null}

            {/* Pagination */}
            {total > PAGE_SIZE ? (
              <div className="mt-10 flex items-center justify-center gap-2">
                <button
                  onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                  disabled={offset === 0 || loading}
                  className="rounded-full glass px-4 py-1.5 text-xs text-slate-300 hover:text-white hover-glow transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setOffset((o) => o + PAGE_SIZE)}
                  disabled={offset + PAGE_SIZE >= total || loading}
                  className="rounded-full glass px-4 py-1.5 text-xs text-slate-300 hover:text-white hover-glow transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            ) : null}
          </>
        )}
      </div>
    </main>
  );
}

function DocumentCard({
  doc,
  delay,
}: {
  doc: DocumentSummary;
  delay: number;
}) {
  const sourceLabel =
    doc.source === "tx_glo"
      ? "Texas GLO"
      : doc.source === "sec_edgar"
        ? "SEC EDGAR"
        : doc.source;
  const sourceTint =
    doc.source === "tx_glo"
      ? "text-violet-300 bg-violet-400/10"
      : doc.source === "sec_edgar"
        ? "text-cyan-300 bg-cyan-400/10"
        : "text-slate-300 bg-slate-400/10";
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      <Link
        href={`/documents/${encodeURIComponent(doc.source)}/${encodeURIComponent(doc.source_id)}`}
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
          <span className="font-mono text-[10px] text-slate-500">
            {doc.page_count}p
          </span>
        </div>
        <h3 className="mt-3 text-sm font-medium text-white leading-snug line-clamp-2">
          {doc.title || `${doc.source} / ${doc.source_id}`}
        </h3>
        <div className="mt-3 flex items-center justify-between text-[11px]">
          <span className="font-mono text-slate-500">{doc.source_id}</span>
          <ArrowUpRight className="h-3.5 w-3.5 text-slate-500 group-hover:text-cyan-300 transition-colors" />
        </div>
      </Link>
    </motion.div>
  );
}
