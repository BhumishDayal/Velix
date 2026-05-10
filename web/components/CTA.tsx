"use client";

import { motion } from "framer-motion";
import { Github, BookOpen } from "lucide-react";
import { GITHUB_URL } from "@/lib/site";

export function CTA() {
  return (
    <section id="cta" className="relative py-32 sm:py-40">
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          className="relative overflow-hidden rounded-3xl glass-strong ring-glow px-8 py-16 sm:px-16 sm:py-24 text-center"
        >
          {/* Layered backgrounds */}
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute inset-0 bg-grid bg-grid-fade opacity-50" />
            <div className="absolute -inset-x-20 -top-20 h-72 bg-[radial-gradient(ellipse_at_center,_rgba(139,92,246,0.4),_transparent_70%)] blur-2xl" />
            <div className="absolute -inset-x-20 -bottom-24 h-64 bg-[radial-gradient(ellipse_at_center,_rgba(34,211,238,0.35),_transparent_70%)] blur-2xl" />
          </div>

          <div className="relative">
            <motion.h2
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0.05 }}
              className="text-[clamp(2rem,5vw,3.5rem)] font-semibold tracking-[-0.03em] leading-[1.05] text-gradient"
            >
              The repo is the demo.
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0.15 }}
              className="mx-auto mt-5 max-w-xl text-base sm:text-lg text-slate-300/85 leading-relaxed"
            >
              Code, tests, schemas, and the build scripts that produced the
              corpus are all open. Read the README, clone, run the test suite.
              The hosted demo follows once the backend is live.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0.25 }}
              className="mt-10 flex flex-wrap items-center justify-center gap-3"
            >
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noreferrer noopener"
                className="group relative inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-medium text-white shadow-glow"
              >
                <span className="absolute inset-0 rounded-full bg-gradient-to-r from-violet-500 to-cyan-400" />
                <span className="absolute inset-px rounded-full bg-gradient-to-r from-violet-500 to-cyan-400" />
                <Github className="relative h-4 w-4" />
                <span className="relative">View on GitHub</span>
              </a>
              <a
                href={`${GITHUB_URL}#readme`}
                target="_blank"
                rel="noreferrer noopener"
                className="group inline-flex items-center gap-2 rounded-full glass px-6 py-3 text-sm font-medium text-slate-200 hover:text-white hover-glow transition-all"
              >
                <BookOpen className="h-3.5 w-3.5 text-cyan-300" />
                Read the README
              </a>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
