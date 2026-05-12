"use client";

import { motion, useReducedMotion } from "framer-motion";

export function AmbientBackground() {
  const reduce = useReducedMotion();
  return (
    <div
      aria-hidden
      className="fixed inset-0 -z-10 overflow-hidden bg-ink-950"
    >
      {/* Base gradient */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(76,29,149,0.18),_transparent_45%),radial-gradient(ellipse_at_bottom,_rgba(8,145,178,0.10),_transparent_55%)]" />

      {/* Dot grid mask */}
      <div className="absolute inset-0 bg-grid bg-grid-fade opacity-70" />

      {/* Drifting orbs */}
      <motion.div
        className="orb h-[520px] w-[520px] left-[-160px] top-[-120px]"
        style={{
          background:
            "radial-gradient(circle at 30% 30%, rgba(139,92,246,0.55), transparent 60%)",
        }}
        animate={
          reduce
            ? undefined
            : { y: [0, -30, 0], x: [0, 20, 0] }
        }
        transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="orb h-[640px] w-[640px] right-[-200px] top-[200px]"
        style={{
          background:
            "radial-gradient(circle at 70% 30%, rgba(34,211,238,0.40), transparent 60%)",
        }}
        animate={
          reduce ? undefined : { y: [0, 40, 0], x: [0, -25, 0] }
        }
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="orb h-[560px] w-[560px] left-[40%] top-[60%]"
        style={{
          background:
            "radial-gradient(circle at 50% 50%, rgba(59,130,246,0.32), transparent 60%)",
        }}
        animate={
          reduce ? undefined : { y: [0, -25, 0], x: [0, 30, 0] }
        }
        transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Top fog & bottom fade so sections blend */}
      <div className="absolute inset-x-0 top-0 h-72 bg-gradient-to-b from-ink-950 via-ink-950/40 to-transparent" />
      <div className="absolute inset-x-0 bottom-0 h-72 bg-gradient-to-t from-ink-950 via-ink-950/40 to-transparent" />
    </div>
  );
}
