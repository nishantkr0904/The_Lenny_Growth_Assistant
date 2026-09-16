/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          500: '#0284c7',
          600: '#0369a1',
          700: '#075985',
        },
        refusal: {
          bg: '#FEF9EF',
          border: '#FDE68A',
          text: '#92400E',
        }
      },
      borderRadius: {
        'button': '6px',
        'card': '8px',
      }
    },
  },
  plugins: [],
}
