/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx}", "./public/index.html"],
  theme: {
    extend: {
      colors: {
        surface: {
          950: "#050505",
          900: "#0e0e10",
          800: "#18181c",
          700: "#202028",
        },
        accent: {
          300: "#c084fc",
          400: "#a855f7",
          500: "#9333ea",
        },
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(192, 132, 252, 0.18), 0 18px 60px rgba(0, 0, 0, 0.45)",
      },
      backgroundImage: {
        halo: "radial-gradient(circle at top, rgba(168, 85, 247, 0.12), transparent 35%), radial-gradient(circle at bottom right, rgba(59, 130, 246, 0.09), transparent 25%)",
      },
    },
  },
  plugins: [],
};
