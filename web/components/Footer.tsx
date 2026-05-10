"use client";

import { motion } from "framer-motion";
import { Github } from "lucide-react";
import { GITHUB_URL, AUTHOR_NAME } from "@/lib/site";

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer id="footer" className="relative pt-16 pb-10">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="hr-fade mb-12" />
        <div className="flex flex-col gap-8 sm:flex-row sm:items-center sm:justify-between">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="flex items-center gap-2.5"
          >
            <span className="relative inline-flex h-7 w-7 items-center justify-center">
              <span className="absolute inset-0 rounded-md bg-gradient-to-br from-violet-500 to-cyan-400 opacity-90" />
              <span className="absolute inset-[2px] rounded-[5px] bg-ink-950" />
              <span className="absolute inset-[5px] rounded-[3px] bg-gradient-to-br from-violet-400 to-cyan-300" />
            </span>
            <span className="text-sm font-semibold text-white tracking-tight">
              Velix
            </span>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.05 }}
          >
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer noopener"
              aria-label="GitHub"
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg glass text-slate-300 hover:text-white hover-glow transition-all"
            >
              <Github className="h-4 w-4" />
            </a>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="mt-10 text-xs text-slate-500"
        >
          © {year} {AUTHOR_NAME}. Released under the MIT License.
        </motion.div>
      </div>
    </footer>
  );
}
