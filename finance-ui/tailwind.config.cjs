/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: {
    colors: { canvas: '#0A0B0D', panel: '#121416', elevated: '#16191C', mint: '#2DD4BF', lime: '#84CC16' },
    fontFamily: { sans: ['Inter', 'Plus Jakarta Sans', 'system-ui', 'sans-serif'] },
  } },
  plugins: [],
}
