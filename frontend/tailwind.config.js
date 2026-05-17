/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          bg:     '#0f172a',
          card:   '#1e293b',
          border: '#334155',
          accent: '#38bdf8',
          red:    '#f87171',
          green:  '#4ade80',
          muted:  '#94a3b8',
        },
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      keyframes: {
        'fade-in': { '0%': { opacity: '0', transform: 'translate(-50%, 8px)' }, '100%': { opacity: '1', transform: 'translate(-50%, 0)' } },
      },
      animation: {
        'fade-in': 'fade-in 0.2s ease-out',
      },
    },
  },
  plugins: [],
}
