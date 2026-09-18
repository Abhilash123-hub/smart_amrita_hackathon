/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Table 13.1 - Core surface and text tokens
        "bg-root": "var(--bg-root)",
        "bg-panel": "var(--bg-panel)",
        "bg-panel-2": "var(--bg-panel-2)",
        "bg-elevated": "var(--bg-elevated)",
        "border-subtle": "var(--border-subtle)",
        "border-strong": "var(--border-strong)",
        "text-primary": "var(--text-primary)",
        "text-body": "var(--text-body)",
        "text-muted": "var(--text-muted)",
        "text-faint": "var(--text-faint)",
        "accent-brand": "var(--accent-brand)",
        "accent-secondary": "var(--accent-secondary)",

        // Table 13.2 - Signal and status colors
        "status-blocked": "var(--status-blocked)",
        "status-review": "var(--status-review)",
        "status-passed": "var(--status-passed)",
        "status-info": "var(--status-info)",
        "risk-high": "var(--risk-high)",
        "risk-mid": "var(--risk-mid)",
        "risk-low": "var(--risk-low)",
      },
    },
  },
  plugins: [],
};
