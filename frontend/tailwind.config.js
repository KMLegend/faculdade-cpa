/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Faixas do ISG herdadas do painel 2024 (doc 08 §3.7)
        isg: {
          grave: '#b91c1c',
          critico: '#ea580c',
          atencao: '#ca8a04',
          bom: '#15803d',
        },
      },
    },
  },
  plugins: [],
}
