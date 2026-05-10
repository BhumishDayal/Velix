"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, Github } from "lucide-react";
import { cn } from "@/lib/utils";
import { GITHUB_URL } from "@/lib/site";

const NAV_ITEMS = [
  { label: "Overview", href: "#overview" },
  { label: "Architecture", href: "#architecture" },
  { label: "Status", href: "#status" },
] as const;

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.header
      initial={{ y: -28, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "fixed top-0 inset-x-0 z-50 transition-all duration-500",
        scrolled ? "pt-3" : "pt-6",
      )}
    >
      <nav
        className={cn(
          "mx-auto flex items-center justify-between gap-4 transition-all duration-500",
          "max-w-6xl px-4 sm:px-6",
          scrolled
            ? "rounded-2xl glass-strong px-3 py-2.5 shadow-glow w-[calc(100%-1.5rem)] sm:w-[calc(100%-3rem)]"
            : "py-3",
        )}
      >
        <a href="#" className="flex items-center gap-2 group">
          <Logo />
          <span className="text-sm font-semibold tracking-tight text-white">
            Velix
          </span>
        </a>

        <div className="hidden md:flex items-center gap-1">
          {NAV_ITEMS.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="relative px-3 py-1.5 text-sm text-slate-300/90 hover:text-white transition-colors"
            >
              <span className="relative z-10">{item.label}</span>
              <span className="absolute inset-x-3 bottom-0.5 h-px scale-x-0 bg-gradient-to-r from-transparent via-violet-400 to-transparent transition-transform duration-300 hover:scale-x-100" />
            </a>
          ))}
        </div>

        <div className="hidden md:flex items-center gap-2">
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer noopener"
            className="group inline-flex items-center gap-1.5 rounded-full px-4 py-1.5 text-sm font-medium text-white bg-gradient-to-r from-violet-500/90 to-cyan-500/90 hover:from-violet-400 hover:to-cyan-400 transition-all shadow-glow ring-1 ring-white/10"
          >
            <Github className="h-3.5 w-3.5" />
            View on GitHub
          </a>
        </div>

        <button
          aria-label="Toggle menu"
          onClick={() => setOpen((v) => !v)}
          className="md:hidden inline-flex h-9 w-9 items-center justify-center rounded-lg glass text-slate-200"
        >
          {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </button>
      </nav>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="md:hidden mx-auto mt-2 max-w-6xl px-4 sm:px-6"
          >
            <div className="rounded-2xl glass-strong p-3">
              {NAV_ITEMS.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className="block rounded-lg px-3 py-2 text-sm text-slate-200 hover:bg-white/5"
                >
                  {item.label}
                </a>
              ))}
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noreferrer noopener"
                onClick={() => setOpen(false)}
                className="mt-1 flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-white bg-gradient-to-r from-violet-500/90 to-cyan-500/90"
              >
                <Github className="h-3.5 w-3.5" />
                View on GitHub
              </a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}

function Logo() {
  return (
    <span className="relative inline-flex h-7 w-7 items-center justify-center">
      <span className="absolute inset-0 rounded-md bg-gradient-to-br from-violet-500 to-cyan-400 opacity-90" />
      <span className="absolute inset-[2px] rounded-[5px] bg-ink-950" />
      <span className="absolute inset-[5px] rounded-[3px] bg-gradient-to-br from-violet-400 to-cyan-300" />
      <span className="absolute inset-0 rounded-md ring-1 ring-white/15" />
    </span>
  );
}
