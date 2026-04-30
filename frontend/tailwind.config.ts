import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "Geist", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Geist Mono", "ui-monospace", "monospace"]
      },
      colors: {
        base: "var(--bg-base)",
        elevated: "var(--bg-elevated)",
        glass: "var(--bg-glass)",
        primary: "var(--fg-primary)",
        secondary: "var(--fg-secondary)",
        muted: "var(--fg-muted)",
        accent: "var(--accent-primary)",
        cyan: "var(--accent-secondary)",
        profit: "var(--profit)",
        loss: "var(--loss)",
        warning: "var(--warning)"
      }
    }
  },
  plugins: []
};

export default config;

