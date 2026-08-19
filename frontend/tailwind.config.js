/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        console: {
          bg: "#0A0D0B",
          panel: "#101512",
          panelRaised: "#151B17",
          border: "#26332C",
          text: "#D7E4DD",
          muted: "#5B6B62",
          good: "#3DDC84",
          warn: "#F5A623",
          critical: "#FF5A4E",
          info: "#5CC8FF",
        },
      },
      fontFamily: {
        mono: ["IBM Plex Mono", "JetBrains Mono", "monospace"],
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glowGood: "0 0 8px rgba(61, 220, 132, 0.35)",
        glowWarn: "0 0 8px rgba(245, 166, 35, 0.35)",
        glowCritical: "0 0 8px rgba(255, 90, 78, 0.35)",
      },
    },
  },
  plugins: [],
};
