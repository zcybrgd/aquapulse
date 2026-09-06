/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#0B2436",
        teal: {
          DEFAULT: "#08A6A6",
          accent: "#2DD4BF",
          light: "#E8F8F7",
        },
        page: "#F6F9FA",
        ink: {
          DEFAULT: "#142B38",
          muted: "#647780",
        },
        warning: "#F59E0B",
        critical: "#E5484D",
        success: "#22A06B",
        line: "#E3ECEF",
      },
      borderRadius: {
        card: "16px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(11, 36, 54, 0.04), 0 8px 24px rgba(11, 36, 54, 0.04)",
      },
      fontFamily: {
        sans: ["DM Sans", "Segoe UI", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
