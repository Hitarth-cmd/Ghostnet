import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ocean: {
          950: "#050b14",
          900: "#0a121f",
          800: "#10192b",
          700: "#182338",
          600: "#233150",
        },
      },
    },
  },
  plugins: [],
};
export default config;
