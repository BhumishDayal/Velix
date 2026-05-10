"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Circle } from "lucide-react";
import { SectionHeading } from "./Features";

const phases = [
  {
    label: "Phase 0",
    title: "Stabilization",
    body: "Tier-routing orchestrator hardened. Fuzzy party-name matching. Pipeline integration tests.",
    done: true,
  },
  {
    label: "Phase 1",
    title: "Corpus",
    body: "194 public oil & gas documents, 3,844 pages, assembled from SEC EDGAR and Texas GLO archives.",
    done: true,
  },
  {
    label: "Phase 2",
    title: "Visual retrieval",
    body: "ColPali / ColQwen2 embedder, Qdrant multi-vector index, MaxSim search. CPU-side complete; GPU activation pending.",
    done: true,
  },
  {
    label: "Phase 3",
    title: "Structured extraction",
    body: "Pydantic schemas for six oil & gas document types. Mock extractor in tests; Qwen2.5-VL backend deferred to GPU.",
    done: true,
  },
  {
    label: "Phase 4",
    title: "Backend on Modal",
    body: "FastAPI service with serverless GPU bursts. In progress.",
    done: false,
  },
  {
    label: "Phase 5",
    title: "Frontend",
    body: "Next.js on Netlify. The page you are reading is part of this phase.",
    done: false,
  },
] as const;

export function Stats() {
  return (
    <section id="status" className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <SectionHeading
          align="center"
          eyebrow="Status"
          title="What is actually built."
          subtitle="No projections, no roadmap fantasies. Every item below either exists in the repo today or it does not."
        />

        <div className="mt-16 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {phases.map((phase, i) => (
            <motion.div
              key={phase.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.6, delay: i * 0.06, ease: [0.16, 1, 0.3, 1] }}
              className={`relative rounded-2xl glass ring-glow p-6 ${
                phase.done ? "" : "opacity-80"
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-[10px] uppercase tracking-[0.25em] text-slate-500">
                    {phase.label}
                  </div>
                  <h3 className="mt-1.5 text-base font-semibold tracking-tight text-white">
                    {phase.title}
                  </h3>
                </div>
                {phase.done ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-400/10 text-emerald-300 px-2 py-0.5 text-[10px] font-medium">
                    <CheckCircle2 className="h-3 w-3" />
                    shipped
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-300/10 text-amber-200 px-2 py-0.5 text-[10px] font-medium">
                    <Circle className="h-3 w-3" />
                    in progress
                  </span>
                )}
              </div>
              <p className="mt-3 text-sm leading-relaxed text-slate-300/80">
                {phase.body}
              </p>
            </motion.div>
          ))}
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mt-10 text-center text-xs text-slate-500"
        >
          Source of truth is the README in the repo. This page is updated when
          the README is.
        </motion.p>
      </div>
    </section>
  );
}
