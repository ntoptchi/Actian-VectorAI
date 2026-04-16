import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07111f",
        mist: "#d9e5f3",
        ember: "#ff7a59",
        surge: "#32c8a2",
        signal: "#7dd3fc",
        midnight: "#0d1728",
      },
      boxShadow: {
        glow: "0 24px 80px rgba(11, 20, 37, 0.35)",
      },
      fontFamily: {
        sans: ["'Space Grotesk'", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      backgroundImage: {
        grid: "linear-gradient(rgba(125, 211, 252, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(125, 211, 252, 0.08) 1px, transparent 1px)",
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
