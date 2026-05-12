"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, Github } from "lucide-react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { GITHUB_URL } from "@/lib/site";

type NavItem = { label: string; href: string };

const NAV_LANDING: readonly NavItem[] = [
  { label: "Overview", href: "/#overview" },
  { label: "Architecture", href: "/#architecture" },
  { label: "Search", href: "/search" },
  { label: "Documents", href: "/documents" },
] as const;

const NAV_APP: readonly NavItem[] = [
  { label: "Home", href: "/" },
  { label: "Search", href: "/search" },
  { label: "Documents", href: "/documents" },
] as const;

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const pathname = usePathname() ?? "/";
  const items = pathname === "/" ? NAV_LANDING : NAV_APP;

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Close mobile menu on route change.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  const lifted = scrolled || pathname !== "/";

  return (
    <motion.header
      initial={{ y: -28, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "fixed top-0 inset-x-0 z-50 transition-all duration-500",
        lifted ? "pt-3" : "pt-6",
      )}
    >
      <nav className="relative mx-auto max-w-6xl px-4 sm:px-6 py-3">
        {/* Glass card — always rendered, opacity fades to avoid border snap */}
        <div
          aria-hidden
          className={cn(
            "absolute inset-x-4 sm:inset-x-6 inset-y-0 rounded-2xl glass-strong shadow-glow",
            "transition-opacity duration-500 will-change-[opacity]",
            lifted ? "opacity-100" : "opacity-0",
          )}
        />
        <div className="relative flex items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-2 group">
          <Logo />
          <span className="text-sm font-semibold tracking-tight text-white">
            Velix
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-1">
          {items.map((item) => {
            const isActive = isItemActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "relative px-3 py-1.5 text-sm transition-colors",
                  isActive
                    ? "text-white"
                    : "text-slate-300/90 hover:text-white",
                )}
              >
                <span className="relative z-10">{item.label}</span>
                {isActive ? (
                  <motion.span
                    layoutId="nav-underline"
                    className="absolute inset-x-3 bottom-0.5 h-px bg-gradient-to-r from-transparent via-violet-400 to-transparent"
                    transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                  />
                ) : null}
              </Link>
            );
          })}
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
        </div>
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
              {items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "block rounded-lg px-3 py-2 text-sm hover:bg-white/5",
                    isItemActive(pathname, item.href)
                      ? "text-white bg-white/5"
                      : "text-slate-200",
                  )}
                >
                  {item.label}
                </Link>
              ))}
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noreferrer noopener"
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

function isItemActive(pathname: string, href: string): boolean {
  if (href.startsWith("/#")) return false; // landing-page anchors don't get active styling
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(href + "/");
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
