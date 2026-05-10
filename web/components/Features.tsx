"use client";

import { motion } from "framer-motion";
import { Eye, ShieldCheck, Layers, Sparkle } from "lucide-react";

const items = [
  {
    icon: Eye,
    title: "Visual retrieval",
    body: "Pages are indexed as images using ColQwen2 multi-vector embeddings. No OCR step on the retrieval path.",
    accent: "from-violet-500/30 to-fuchsia-500/10",
    iconTint: "text-violet-300",
  },
  {
    icon: ShieldCheck,
    title: "Typed extraction",
    body: "Output is constrained by Pydantic schemas for six oil and gas document types. Invalid output is rejected, not coerced.",
    accent: "from-cyan-400/30 to-sky-500/10",
    iconTint: "text-cyan-300",
  },
  {
    icon: Layers,
    title: "Composable layers",
    body: "Embedder, schema, and store are independent. Mock implementations let the whole pipeline run on CPU for tests.",
    accent: "from-emerald-400/25 to-teal-500/10",
    iconTint: "text-emerald-300",
  },
  {
    icon: Sparkle,
    title: "On-demand by design",
    body: "Indexing runs once per page. Field extraction runs only when a page is queried. Compute follows usage, not corpus size.",
    accent: "from-amber-300/25 to-orange-500/10",
    iconTint: "text-amber-200",
  },
] as const;

export function Features() {
  return (
    <section className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <SectionHeading
          eyebrow="Approach"
          title="Four ideas the whole project rests on."
        />

        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {items.map((item, i) => (
            <FeatureCard key={item.title} {...item} delay={i * 0.08} />
          ))}
        </div>
      </div>
    </section>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  body,
  accent,
  iconTint,
  delay,
}: (typeof items)[number] & { delay: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}
      className="group relative rounded-2xl glass ring-glow p-6 hover-glow transition-all duration-300 will-change-transform hover:-translate-y-1"
    >
      <div
        className={`pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-br ${accent} opacity-0 transition-opacity duration-500 group-hover:opacity-100`}
      />
      <div className="relative">
        <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl glass-strong ring-1 ring-white/10">
          <Icon className={`h-4.5 w-4.5 ${iconTint}`} />
        </div>
        <h3 className="mt-5 text-lg font-semibold tracking-tight text-white">
          {title}
        </h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-300/80">
          {body}
        </p>
      </div>
    </motion.div>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  subtitle,
  align = "left",
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  align?: "left" | "center";
}) {
  const isCenter = align === "center";
  return (
    <div className={isCenter ? "text-center max-w-3xl mx-auto" : "max-w-2xl"}>
      {eyebrow ? (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5 }}
          className="text-xs uppercase tracking-[0.3em] text-cyan-300/80"
        >
          {eyebrow}
        </motion.div>
      ) : null}
      <motion.h2
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.7, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
        className="mt-3 text-[clamp(1.75rem,4.5vw,2.75rem)] font-semibold tracking-[-0.025em] leading-tight text-gradient"
      >
        {title}
      </motion.h2>
      {subtitle ? (
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.7, delay: 0.12 }}
          className="mt-4 text-base text-slate-300/80 leading-relaxed"
        >
          {subtitle}
        </motion.p>
      ) : null}
    </div>
  );
}
