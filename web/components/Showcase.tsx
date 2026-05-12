"use client";

import { motion, useReducedMotion } from "framer-motion";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { SectionHeading } from "./Features";

export function Showcase() {
  return (
    <section
      id="architecture"
      className="relative py-24 sm:py-32 overflow-hidden"
    >
      <div className="pointer-events-none absolute -top-1/2 left-1/4 h-[200%] w-px bg-gradient-to-b from-transparent via-violet-500/20 to-transparent rotate-12" />

      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="grid lg:grid-cols-12 gap-12 lg:gap-10 items-center">
          {/* Left: dashboard-style mock */}
          <div className="lg:col-span-7 order-2 lg:order-1">
            <DashboardMock />
          </div>

          {/* Right: copy */}
          <div className="lg:col-span-5 order-1 lg:order-2">
            <SectionHeading
              eyebrow="The Workspace"
              title="One screen for the page, the fields, and the checks."
              subtitle="The PDF on the left, the typed extraction on the right, validators showing their work. Click into any indexed document and try it."
            />

            <ul className="mt-8 space-y-4">
              {[
                "Source PDF rendered inline, scrollable, zoomable.",
                "Pydantic-typed fields mirror the document's schema; what you see is what feeds the LLM.",
                "Domain validators (PLSS, mineral fractions, party chains) show pass or fail per field.",
              ].map((line, i) => (
                <motion.li
                  key={line}
                  initial={{ opacity: 0, x: -8 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true, margin: "-100px" }}
                  transition={{ duration: 0.6, delay: i * 0.08 }}
                  className="flex items-start gap-3 text-sm text-slate-300/85"
                >
                  <span className="mt-1.5 h-1.5 w-1.5 flex-none rounded-full bg-gradient-to-br from-violet-400 to-cyan-300 shadow-[0_0_8px_rgba(139,92,246,0.7)]" />
                  <span>{line}</span>
                </motion.li>
              ))}
            </ul>

            <div className="mt-8">
              <Link
                href="/documents/tx_glo/9113"
                className="group inline-flex items-center gap-2 rounded-full glass px-4 py-2 text-sm font-medium text-slate-200 hover:text-white hover-glow transition-all"
              >
                Open this document
                <ArrowUpRight className="h-3.5 w-3.5 text-cyan-300 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function DashboardMock() {
  const reduce = useReducedMotion();
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-120px" }}
      transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
      className="relative"
    >
      <div className="pointer-events-none absolute -inset-12 rounded-[2.5rem] bg-gradient-to-br from-violet-500/15 via-transparent to-cyan-500/15 blur-3xl" />

      <div className="relative rounded-2xl glass-strong ring-glow overflow-hidden">
        {/* Window chrome */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
          <div className="flex items-center gap-1.5">
            <div className="h-2.5 w-2.5 rounded-full bg-rose-400/70" />
            <div className="h-2.5 w-2.5 rounded-full bg-amber-300/70" />
            <div className="h-2.5 w-2.5 rounded-full bg-emerald-400/70" />
          </div>
          <div className="hidden sm:flex items-center gap-2 rounded-md bg-white/5 px-2.5 py-1 text-[11px] font-mono text-slate-400">
            <span className="text-slate-500">velix</span>
            <span>/document/9113</span>
          </div>
          <div className="text-[10px] uppercase tracking-[0.25em] text-slate-500">
            workspace
          </div>
        </div>

        <div className="grid grid-cols-12 min-h-[440px]">
          {/* Left rail */}
          <div className="col-span-2 hidden md:flex flex-col gap-1 p-3 border-r border-white/5 bg-white/[0.015]">
            {["Inbox", "Documents", "Search", "Schemas", "Settings"].map(
              (label, i) => (
                <div
                  key={label}
                  className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-[11px] ${
                    i === 1
                      ? "bg-violet-500/15 text-violet-200"
                      : "text-slate-400"
                  }`}
                >
                  <span className="h-1 w-1 rounded-full bg-current opacity-70" />
                  {label}
                </div>
              ),
            )}
          </div>

          {/* Document canvas */}
          <div className="col-span-12 md:col-span-7 relative p-5 border-r border-white/5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase tracking-[0.25em] text-slate-500">
                  Page 14
                </span>
              </div>
            </div>

            <DocumentBody reduce={!!reduce} />
          </div>

          {/* Right side panel */}
          <div className="col-span-12 md:col-span-3 p-4 bg-white/[0.012]">
            <div className="text-[10px] uppercase tracking-[0.25em] text-slate-500 mb-3">
              MineralDeed
            </div>
            <SidePanelField k="grantor" v="Smith Family Trust" />
            <SidePanelField k="grantee" v="ABC Minerals LLC" />
            <SidePanelField k="fraction" v="1/64" mono />
            <SidePanelField k="section" v="14" mono />
            <SidePanelField k="township" v="T2N" mono />
            <SidePanelField k="range" v="R3W" mono />
            <SidePanelField k="county" v="Reeves, TX" />

            <div className="mt-5 rounded-xl glass p-3">
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500 mb-2">
                Validators
              </div>
              <div className="space-y-1.5 text-[11px]">
                <ValidationRow label="PLSS parses" ok />
                <ValidationRow label="Power-of-two denom." ok />
                <ValidationRow label="Chain consistency" ok />
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function DocumentBody({ reduce }: { reduce: boolean }) {
  return (
    <div className="relative h-72 rounded-md bg-white/[0.025] border border-white/5 overflow-hidden p-4">
      <div className="space-y-2.5">
        {Array.from({ length: 11 }).map((_, i) => (
          <div
            key={i}
            className="h-2 rounded-full bg-white/5"
            style={{ width: `${72 + ((i * 17) % 24)}%` }}
          />
        ))}
      </div>
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ delay: 0.6 }}
        className="absolute left-4 top-[68px] h-3 w-32 rounded border border-violet-300/50 bg-violet-300/10"
      >
        <span className="absolute -top-4 left-0 rounded bg-violet-400/90 text-ink-950 px-1.5 py-px text-[8px] font-mono">
          grantor
        </span>
      </motion.div>
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ delay: 0.85 }}
        className="absolute left-32 top-[100px] h-3 w-28 rounded border border-cyan-300/50 bg-cyan-300/10"
      >
        <span className="absolute -top-4 left-0 rounded bg-cyan-400/90 text-ink-950 px-1.5 py-px text-[8px] font-mono">
          grantee
        </span>
      </motion.div>
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ delay: 1.05 }}
        className="absolute left-24 top-[156px] h-3 w-14 rounded border border-emerald-300/50 bg-emerald-300/10"
      >
        <span className="absolute -top-4 left-0 rounded bg-emerald-400/90 text-ink-950 px-1.5 py-px text-[8px] font-mono">
          1/64
        </span>
      </motion.div>

      {!reduce && (
        <motion.div
          className="pointer-events-none absolute inset-y-0 -left-1/3 w-1/3 bg-gradient-to-r from-transparent via-white/10 to-transparent"
          animate={{ x: ["0%", "400%"] }}
          transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
        />
      )}
    </div>
  );
}

function SidePanelField({
  k,
  v,
  mono,
}: {
  k: string;
  v: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-1.5 text-[11px] border-b border-white/5 last:border-b-0">
      <span className="text-slate-400">{k}</span>
      <span className={mono ? "font-mono text-cyan-300" : "text-slate-100"}>
        {v}
      </span>
    </div>
  );
}

function ValidationRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between text-slate-300">
      <span>{label}</span>
      <span
        className={`inline-flex items-center gap-1 ${
          ok ? "text-emerald-300" : "text-rose-300"
        }`}
      >
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            ok ? "bg-emerald-400" : "bg-rose-400"
          }`}
        />
        {ok ? "pass" : "fail"}
      </span>
    </div>
  );
}
