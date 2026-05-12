"use client";

import { useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { ChevronLeft, ChevronRight, Loader2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.mjs`;

const PDF_OPTIONS = {
  cMapUrl: `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/cmaps/`,
  standardFontDataUrl: `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/standard_fonts/`,
};

export function PdfViewer({
  url,
  initialPageCount,
  pageNumber: controlledPage,
  onPageChange,
}: {
  url: string;
  initialPageCount?: number;
  pageNumber?: number;
  onPageChange?: (page: number) => void;
}) {
  const [numPages, setNumPages] = useState<number>(initialPageCount ?? 0);
  const [internalPage, setInternalPage] = useState<number>(1);
  const [error, setError] = useState<Error | null>(null);
  const [width, setWidth] = useState<number>(600);
  const containerRef = useRef<HTMLDivElement>(null);

  const pageNumber = controlledPage ?? internalPage;
  const setPageNumber = (next: number) => {
    if (onPageChange) onPageChange(next);
    if (controlledPage === undefined) setInternalPage(next);
  };

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const measure = () => setWidth(Math.max(280, el.clientWidth - 32));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (controlledPage === undefined) setInternalPage(1);
    setError(null);
  }, [url, controlledPage]);

  const canPrev = pageNumber > 1;
  const canNext = numPages > 0 && pageNumber < numPages;

  return (
    <div className="rounded-2xl glass-strong ring-glow overflow-hidden h-[640px] flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/5 bg-ink-900/40">
        <button
          onClick={() => setPageNumber(Math.max(1, pageNumber - 1))}
          disabled={!canPrev}
          className={cn(
            "inline-flex h-7 w-7 items-center justify-center rounded-md transition-colors",
            canPrev
              ? "text-slate-200 hover:bg-white/5"
              : "text-slate-600 cursor-not-allowed",
          )}
          aria-label="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="font-mono text-[11px] text-slate-400">
          {numPages > 0 ? `${pageNumber} / ${numPages}` : "—"}
        </span>
        <button
          onClick={() => setPageNumber(Math.min(numPages, pageNumber + 1))}
          disabled={!canNext}
          className={cn(
            "inline-flex h-7 w-7 items-center justify-center rounded-md transition-colors",
            canNext
              ? "text-slate-200 hover:bg-white/5"
              : "text-slate-600 cursor-not-allowed",
          )}
          aria-label="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      {/* Render area */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto bg-slate-100 px-4 py-4 flex justify-center"
      >
        {error ? (
          <div className="flex flex-col items-center justify-center text-center text-slate-700 max-w-sm">
            <AlertCircle className="h-6 w-6 text-rose-500 mb-2" />
            <div className="text-sm font-medium">Couldn&apos;t load this PDF</div>
            <div className="font-mono text-[11px] text-slate-500 mt-1 break-all">
              {error.message}
            </div>
          </div>
        ) : (
          <Document
            file={url}
            options={PDF_OPTIONS}
            onLoadSuccess={({ numPages }) => setNumPages(numPages)}
            onLoadError={(err) => setError(err)}
            loading={
              <div className="flex items-center gap-2 text-sm text-slate-500 py-8">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading PDF…
              </div>
            }
          >
            <Page
              pageNumber={pageNumber}
              width={width}
              renderTextLayer={false}
              renderAnnotationLayer={false}
              loading={
                <div className="flex items-center gap-2 text-sm text-slate-500 py-8">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Rendering page…
                </div>
              }
            />
          </Document>
        )}
      </div>
    </div>
  );
}
