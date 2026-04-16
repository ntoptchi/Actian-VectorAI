import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b1220",
        mist: "#f3f7fa",
        ember: "#f97316",
        surge: "#14b8a6",
        signal: "#3b82f6",
        midnight: "#0f1726",
        cyan: "#22d3ee",
        warning: "#f59e0b",
        danger: "#ef4444",
      },
      boxShadow: {
        glow: "0 22px 60px rgba(0, 0, 0, 0.38)",
      },
      fontFamily: {
        sans: ["'Noto Sans'", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["'Roboto Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      backgroundImage: {
        grid: "linear-gradient(rgba(59, 130, 246, 0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(59, 130, 246, 0.07) 1px, transparent 1px)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(18px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        rise: "rise 700ms ease-out forwards",
      },
    },
  },
  plugins: [],
} satisfies Config;
