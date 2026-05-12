"use client";

import { use, useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  ArrowLeft,
  ExternalLink,
  Loader2,
  AlertCircle,
} from "lucide-react";
import {
  api,
  type DocumentSummary,
  type ExtractResponse,
  ApiError,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import dynamic from "next/dynamic";
import { InDocSearch } from "@/components/InDocSearch";

// react-pdf initializes pdfjs worker at module load; ssr:false keeps it client-only.
const PdfViewer = dynamic(
  () => import("@/components/PdfViewer").then((m) => m.PdfViewer),
  {
    ssr: false,
    loading: () => (
      <div className="rounded-2xl glass-strong ring-glow h-[640px] flex items-center justify-center text-sm text-slate-400">
        Loading viewer…
      </div>
    ),
  },
);

type Params = { source: string; id: string };

export default function DocumentDetailPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { source, id } = use(params);
  const [doc, setDoc] = useState<DocumentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    api
      .getDocument(source, id, controller.signal)
      .then((d) => setDoc(d))
      .catch((err) => {
        if (controller.signal.aborted) return;
        if (err instanceof ApiError) {
          setError(`backend ${err.status}: ${err.message}`);
        } else {
          setError("couldn't reach the backend");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [source, id]);

  return (
    <main className="relative min-h-screen pt-32 pb-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <Link
          href="/documents"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to documents
        </Link>

        {loading ? (
          <div className="mt-12 flex items-center gap-2 text-sm text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading document…
          </div>
        ) : error ? (
          <ErrorState message={error} />
        ) : doc ? (
          <DocumentDetail doc={doc} />
        ) : null}
      </div>
    </main>
  );
}

function DocumentDetail({ doc }: { doc: DocumentSummary }) {
  const [currentPage, setCurrentPage] = useState<number>(1);

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
  const pdfUrl = api.documentPdfUrl(doc.source, doc.source_id);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="mt-6"
    >
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-medium",
                sourceTint,
              )}
            >
              {sourceLabel}
            </span>
            <span className="font-mono text-[11px] text-slate-500">
              {doc.source_id}
            </span>
            <span className="font-mono text-[11px] text-slate-500">·</span>
            <span className="font-mono text-[11px] text-slate-500">
              {doc.page_count} pages
            </span>
          </div>
          <h1 className="mt-3 text-[clamp(1.5rem,3.5vw,2.25rem)] font-semibold tracking-[-0.02em] leading-tight text-white">
            {doc.title || `${doc.source} / ${doc.source_id}`}
          </h1>
        </div>

        <a
          href={pdfUrl}
          target="_blank"
          rel="noreferrer noopener"
          className="inline-flex items-center gap-1.5 rounded-full glass px-4 py-1.5 text-xs font-medium text-slate-200 hover:text-white hover-glow transition-all whitespace-nowrap"
        >
          <ExternalLink className="h-3.5 w-3.5 text-cyan-300" />
          Open PDF
        </a>
      </div>

      {/* Two columns: PDF preview + side panels */}
      <div className="mt-10 grid lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7">
          <PdfViewer
            url={api.documentPdfUrl(doc.source, doc.source_id)}
            initialPageCount={doc.page_count}
            pageNumber={currentPage}
            onPageChange={setCurrentPage}
          />
        </div>
        <div className="lg:col-span-5 space-y-5">
          <InDocSearch
            source={doc.source}
            sourceId={doc.source_id}
            pageCount={doc.page_count}
            onJumpToPage={setCurrentPage}
            currentPage={currentPage}
          />
          <MetadataPanel doc={doc} />
          <ExtractionPanel doc={doc} />
        </div>
      </div>
    </motion.div>
  );
}

function MetadataPanel({ doc }: { doc: DocumentSummary }) {
  const entries = Object.entries(doc.metadata).filter(
    ([, v]) => v !== "" && v !== null && v !== undefined,
  );
  return (
    <div className="rounded-2xl glass ring-glow p-5">
      <div className="text-[10px] uppercase tracking-[0.25em] text-slate-500 mb-4">
        Source metadata
      </div>
      {entries.length === 0 ? (
        <p className="text-xs text-slate-500">No metadata captured.</p>
      ) : (
        <dl className="space-y-2">
          {entries.map(([k, v]) => (
            <div
              key={k}
              className="flex items-baseline justify-between gap-3 text-[12px] py-1 border-b border-white/5 last:border-b-0"
            >
              <dt className="text-slate-400">{k}</dt>
              <dd className="text-right text-slate-100 font-mono text-[11px] max-w-[60%] break-words">
                {String(v)}
              </dd>
            </div>
          ))}
        </dl>
      )}
      <div className="mt-4 pt-4 border-t border-white/5 flex items-baseline justify-between text-[11px]">
        <span className="text-slate-500">sha256</span>
        <span className="font-mono text-slate-400 truncate max-w-[60%]">
          {doc.sha256 || "—"}
        </span>
      </div>
    </div>
  );
}

const SCHEMAS = [
  { value: "auto", label: "Auto-detect" },
  { value: "mineral_deed", label: "Mineral Deed" },
  { value: "oil_gas_lease", label: "Oil & Gas Lease" },
  { value: "division_order", label: "Division Order" },
  { value: "assignment", label: "Assignment" },
  { value: "ratification", label: "Ratification" },
  { value: "joa_snippet", label: "JOA Snippet" },
] as const;

function inferSchema(doc: DocumentSummary): string {
  const haystack = [
    doc.title || "",
    String(doc.metadata?.title ?? ""),
    String(doc.metadata?.form ?? ""),
    String(doc.metadata?.document_type ?? ""),
  ]
    .join(" ")
    .toLowerCase();
  if (/\bjoa\b|joint operating|operating agreement/.test(haystack))
    return "joa_snippet";
  if (/division order/.test(haystack)) return "division_order";
  if (/ratification/.test(haystack)) return "ratification";
  if (/assignment/.test(haystack)) return "assignment";
  if (/lease/.test(haystack)) return "oil_gas_lease";
  if (/deed|grant/.test(haystack)) return "mineral_deed";
  return "oil_gas_lease";
}

function describeApiError(err: ApiError): string {
  const detail = err.detail as unknown;
  if (typeof detail === "string") return `${err.status}: ${detail}`;
  if (detail && typeof detail === "object") {
    const d = detail as Record<string, unknown>;
    const inner = d.detail ?? d;
    if (typeof inner === "string") return `${err.status}: ${inner}`;
    if (inner && typeof inner === "object") {
      const obj = inner as Record<string, unknown>;
      const msg = typeof obj.message === "string" ? obj.message : null;
      const errs = Array.isArray(obj.errors) ? (obj.errors as unknown[]) : null;
      if (msg && errs && errs.length) {
        const fields = errs
          .map((e) => {
            const eo = e as Record<string, unknown>;
            const loc = Array.isArray(eo.loc) ? eo.loc.join(".") : "";
            return loc || (typeof eo.msg === "string" ? eo.msg : "");
          })
          .filter(Boolean)
          .slice(0, 4)
          .join(", ");
        return `${err.status}: ${msg}${fields ? ` — missing/invalid: ${fields}` : ""}`;
      }
      if (msg) return `${err.status}: ${msg}`;
    }
  }
  return `${err.status}: ${err.message || "request failed"}`;
}

function ExtractionPanel({ doc }: { doc: DocumentSummary }) {
  const inferred = inferSchema(doc);
  const [schema, setSchema] = useState<string>("auto");
  const [page, setPage] = useState<number>(0);
  const [result, setResult] = useState<ExtractResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultFilter, setResultFilter] = useState<string>("");

  const effectiveSchema = schema === "auto" ? inferred : schema;
  const inferredLabel =
    SCHEMAS.find((s) => s.value === inferred)?.label ?? inferred;

  async function run() {
    setLoading(true);
    setError(null);
    setResult(null);
    setResultFilter("");
    try {
      const res = await api.extract({
        source: doc.source,
        source_id: doc.source_id,
        page_number: page,
        schema_name: effectiveSchema,
      });
      setResult(res);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(describeApiError(err));
      } else {
        setError("request failed");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl glass ring-glow p-5">
      <div className="text-[10px] uppercase tracking-[0.25em] text-slate-500 mb-4">
        Structured extraction
      </div>

      <div className="grid grid-cols-2 gap-2">
        <label className="block text-[11px] text-slate-400">
          Schema
          <select
            value={schema}
            onChange={(e) => setSchema(e.target.value)}
            className="mt-1 w-full rounded-lg glass-strong px-2.5 py-1.5 text-[12px] text-white outline-none ring-1 ring-white/10 focus:ring-violet-400/40"
          >
            {SCHEMAS.map((s) => (
              <option key={s.value} value={s.value} className="bg-ink-900">
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-[11px] text-slate-400">
          Page
          <input
            type="number"
            min={0}
            max={Math.max(0, doc.page_count - 1)}
            value={page}
            onChange={(e) => setPage(parseInt(e.target.value || "0", 10))}
            className="mt-1 w-full rounded-lg glass-strong px-2.5 py-1.5 text-[12px] text-white outline-none ring-1 ring-white/10 focus:ring-violet-400/40 font-mono"
          />
        </label>
      </div>

      {schema === "auto" ? (
        <div className="mt-2 text-[10px] text-slate-500">
          Inferred from title:{" "}
          <span className="text-cyan-300/90 font-mono">{inferredLabel}</span>
        </div>
      ) : null}

      <button
        onClick={run}
        disabled={loading}
        className="mt-4 w-full inline-flex items-center justify-center gap-2 rounded-full px-4 py-2 text-xs font-medium text-white bg-gradient-to-r from-violet-500/90 to-cyan-500/90 shadow-glow ring-1 ring-white/10 disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:from-violet-400 hover:to-cyan-400"
      >
        {loading ? (
          <>
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Extracting…
          </>
        ) : (
          <>Extract page {page}</>
        )}
      </button>

      {error ? (
        <div className="mt-4 rounded-lg border border-rose-500/30 bg-rose-500/5 p-3 text-[11px] text-rose-200 flex items-start gap-2">
          <AlertCircle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
          <div className="font-mono">{error}</div>
        </div>
      ) : null}

      {result ? (
        <div className="mt-4 rounded-lg glass-strong p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] uppercase tracking-[0.25em] text-slate-500">
              {result.schema_name}
            </span>
            <span
              className={cn(
                "text-[10px] font-medium px-2 py-0.5 rounded-full",
                result.cached
                  ? "bg-cyan-400/10 text-cyan-300"
                  : "bg-emerald-400/10 text-emerald-300",
              )}
            >
              {result.cached ? "cached" : "fresh"}
            </span>
          </div>
          <input
            value={resultFilter}
            onChange={(e) => setResultFilter(e.target.value)}
            placeholder="Filter fields (e.g. lessor, royalty, county)…"
            className="mb-2 w-full rounded-md bg-white/5 px-2.5 py-1.5 text-[11px] text-white placeholder:text-slate-500 outline-none ring-1 ring-white/10 focus:ring-violet-400/40 font-mono"
          />
          <ExtractionResultView
            extraction={result.extraction}
            filter={resultFilter}
          />
        </div>
      ) : null}
    </div>
  );
}

type FlatRow = { path: string; value: string };

function flattenExtraction(value: unknown, prefix = ""): FlatRow[] {
  const rows: FlatRow[] = [];
  if (value === null || value === undefined) {
    rows.push({ path: prefix || "(root)", value: String(value) });
    return rows;
  }
  if (Array.isArray(value)) {
    if (value.length === 0) {
      rows.push({ path: prefix, value: "[]" });
    } else {
      value.forEach((v, i) => {
        rows.push(...flattenExtraction(v, `${prefix}[${i}]`));
      });
    }
    return rows;
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    if (entries.length === 0) {
      rows.push({ path: prefix, value: "{}" });
    } else {
      for (const [k, v] of entries) {
        rows.push(...flattenExtraction(v, prefix ? `${prefix}.${k}` : k));
      }
    }
    return rows;
  }
  rows.push({ path: prefix, value: String(value) });
  return rows;
}

function ExtractionResultView({
  extraction,
  filter,
}: {
  extraction: Record<string, unknown>;
  filter: string;
}) {
  const rows = flattenExtraction(extraction);
  const q = filter.trim().toLowerCase();
  const filtered = q
    ? rows.filter(
        (r) =>
          r.path.toLowerCase().includes(q) ||
          r.value.toLowerCase().includes(q),
      )
    : rows;

  if (filtered.length === 0) {
    return (
      <div className="text-[11px] text-slate-500 italic">
        No fields match &ldquo;{filter}&rdquo;.
      </div>
    );
  }

  return (
    <div className="max-h-80 overflow-y-auto pr-1 space-y-1">
      {filtered.map((r, i) => (
        <div
          key={`${r.path}-${i}`}
          className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] gap-3 text-[11px] py-1 border-b border-white/5 last:border-b-0"
        >
          <div className="font-mono text-slate-400 truncate" title={r.path}>
            <FilterHighlight text={r.path} query={q} />
          </div>
          <div className="font-mono text-slate-100 break-words">
            <FilterHighlight text={r.value} query={q} />
          </div>
        </div>
      ))}
    </div>
  );
}

function FilterHighlight({ text, query }: { text: string; query: string }) {
  if (!query) return <>{text}</>;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, "gi"));
  return (
    <>
      {parts.map((part, i) =>
        part.toLowerCase() === query ? (
          <mark key={i} className="rounded bg-violet-400/30 text-white px-0.5">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="mt-12 rounded-2xl glass border border-rose-500/30 p-6 text-sm text-rose-200">
      <div className="font-medium mb-1">Failed to load document</div>
      <div className="font-mono text-xs text-rose-300/80">{message}</div>
    </div>
  );
}
