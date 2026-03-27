/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        sgmc: {
          50: '#f0f7ff',
          100: '#e0effe',
          200: '#b9dffd',
          300: '#7cc5fb',
          400: '#36a8f6',
          500: '#0c8de7',
          600: '#006fc5',
          700: '#0059a0',
          800: '#054c84',
          900: '#0a406e',
          950: '#072849',
        },
      },
    },
  },
  plugins: [],
}
