"use client";

import { motion, useScroll, useTransform, useReducedMotion } from "framer-motion";
import { ArrowRight, Github } from "lucide-react";
import Link from "next/link";
import { useRef } from "react";
import { GITHUB_URL } from "@/lib/site";
import { LiveStatus } from "./LiveStatus";

export function Hero() {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });
  const y = useTransform(scrollYProgress, [0, 1], [0, reduce ? 0 : -120]);
  const fade = useTransform(scrollYProgress, [0, 1], [1, 0.4]);

  return (
    <section
      ref={ref}
      id="overview"
      className="relative min-h-[100svh] flex items-center pt-32 pb-24"
    >
      {/* Soft conic glow seated behind the visual */}
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <div className="conic-glow h-[820px] w-[820px] rounded-full opacity-60 animate-spin-slow" />
      </div>

      <motion.div
        style={{ y, opacity: fade }}
        className="relative mx-auto w-full max-w-6xl px-4 sm:px-6"
      >
        <div className="grid lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* Copy column */}
          <div className="lg:col-span-7">
            <LiveStatus />

            <motion.h1
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.9, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
              className="mt-6 font-sans text-[clamp(2.6rem,7vw,5.6rem)] font-semibold tracking-[-0.04em] leading-[0.95]"
            >
              <span className="block text-gradient">See the page.</span>
              <span className="block text-gradient-accent mt-2">
                Not just the text.
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.18 }}
              className="mt-6 max-w-xl text-base sm:text-lg text-slate-300/85 leading-relaxed"
            >
              Velix is an open source research project on visual-first
              retrieval and structured extraction for legal and real-asset
              documents. The retrieval and extraction layers are built. A
              hosted demo and frontend integration are next.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.28 }}
              className="mt-9 flex flex-wrap items-center gap-3"
            >
              <Link
                href="/search"
                className="group relative inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm font-medium text-white shadow-glow"
              >
                <span className="absolute inset-0 rounded-full bg-gradient-to-r from-violet-500 to-cyan-400" />
                <span className="absolute inset-px rounded-full bg-gradient-to-r from-violet-500 to-cyan-400 opacity-90 transition group-hover:opacity-100" />
                <span className="relative">Open the demo</span>
                <ArrowRight className="relative h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noreferrer noopener"
                className="group inline-flex items-center gap-2 rounded-full glass px-5 py-3 text-sm font-medium text-slate-200 hover:text-white hover-glow transition-all"
              >
                <Github className="h-3.5 w-3.5 text-cyan-300" />
                View on GitHub
              </a>
            </motion.div>
          </div>

          {/* Product visual column */}
          <div className="lg:col-span-5">
            <HeroVisual />
          </div>
        </div>
      </motion.div>

      {/* Scroll cue */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2, duration: 1 }}
        className="pointer-events-none absolute bottom-8 inset-x-0 flex justify-center"
      >
        <div className="flex flex-col items-center gap-1.5 text-[10px] uppercase tracking-[0.3em] text-slate-500">
          Scroll
          <span className="h-9 w-px bg-gradient-to-b from-slate-500 to-transparent" />
        </div>
      </motion.div>
    </section>
  );
}

function HeroVisual() {
  const reduce = useReducedMotion();
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 1.1, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="relative mx-auto h-[460px] w-full max-w-[460px]"
    >
      {/* Soft halo */}
      <div className="absolute -inset-10 rounded-[3rem] bg-gradient-to-br from-violet-500/15 via-transparent to-cyan-500/15 blur-3xl" />

      {/* Back card (rotated) */}
      <motion.div
        animate={reduce ? undefined : { y: [0, -8, 0] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        className="absolute right-0 top-6 h-72 w-56 rounded-2xl glass ring-glow rotate-[8deg] origin-bottom-left"
      >
        <PageGlyph variant="back" />
      </motion.div>

      {/* Front "page" card */}
      <motion.div
        animate={reduce ? undefined : { y: [0, 10, 0] }}
        transition={{ duration: 9, repeat: Infinity, ease: "easeInOut", delay: 0.6 }}
        className="absolute left-0 top-12 h-80 w-64 rounded-2xl glass-strong ring-glow rotate-[-4deg] overflow-hidden"
      >
        <PageGlyph variant="front" />
      </motion.div>

      {/* Floating extracted-field card */}
      <motion.div
        initial={{ opacity: 0, x: 20, y: -8 }}
        animate={{ opacity: 1, x: 0, y: 0 }}
        transition={{ duration: 1, delay: 0.9 }}
        className="absolute right-[-12px] bottom-6 w-[270px]"
      >
        <motion.div
          animate={reduce ? undefined : { y: [0, -8, 0] }}
          transition={{ duration: 7, repeat: Infinity, ease: "easeInOut", delay: 1.2 }}
          className="rounded-2xl glass-strong ring-glow p-4"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] uppercase tracking-[0.2em] text-slate-400">
              MineralDeed
            </span>
            <span className="rounded-full bg-white/5 text-slate-400 px-2 py-0.5 text-[10px] font-mono">
              schema
            </span>
          </div>
          <FieldRow k="grantor" v="Smith Family Trust" />
          <FieldRow k="grantee" v="ABC Minerals LLC" />
          <FieldRow k="fraction" v="1/64" mono />
          <FieldRow k="section" v="14 · T2N R3W" mono />
        </motion.div>
      </motion.div>
    </motion.div>
  );
}

function FieldRow({
  k,
  v,
  mono,
}: {
  k: string;
  v: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-1.5 text-xs">
      <span className="text-slate-400">{k}</span>
      <span
        className={
          mono
            ? "font-mono text-cyan-300"
            : "text-slate-100"
        }
      >
        {v}
      </span>
    </div>
  );
}

function PageGlyph({ variant }: { variant: "front" | "back" }) {
  const lines = variant === "front" ? 9 : 11;
  return (
    <div className="h-full w-full p-4 flex flex-col gap-2">
      {/* Header bar */}
      <div className="flex items-center gap-1.5">
        <div className="h-1.5 w-1.5 rounded-full bg-rose-400/70" />
        <div className="h-1.5 w-1.5 rounded-full bg-amber-300/70" />
        <div className="h-1.5 w-1.5 rounded-full bg-emerald-400/70" />
        <div className="ml-2 h-1.5 flex-1 rounded-full bg-white/5" />
      </div>
      {/* Page lines */}
      <div className="flex-1 flex flex-col gap-2 mt-2">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="h-1.5 rounded-full bg-white/5"
            style={{ width: `${75 + (i * 13) % 22}%` }}
          />
        ))}
        {/* Highlighted bbox */}
        {variant === "front" && (
          <div className="relative mt-1 h-8 rounded-md border border-cyan-300/40 bg-cyan-300/5">
            <div className="absolute inset-0 rounded-md ring-1 ring-cyan-300/30 animate-pulse-slow" />
            <div className="absolute -top-1.5 left-1.5 rounded bg-cyan-400/90 px-1.5 py-px text-[8px] font-mono text-ink-950">
              fraction
            </div>
          </div>
        )}
        {variant === "back" && (
          <div className="relative mt-1 h-8 rounded-md border border-violet-300/40 bg-violet-300/5">
            <div className="absolute -top-1.5 left-1.5 rounded bg-violet-400/90 px-1.5 py-px text-[8px] font-mono text-ink-950">
              party
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
