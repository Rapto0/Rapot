import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        background: "#0e1117",
        panel: "#161b22",
        accent: "#2962ff",
        long: "#00c853",
        short: "#ff3d00"
      }
    }
  },
  plugins: []
};

export default config;
