/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: { sans: ['Inter', 'system-ui', 'Segoe UI', 'sans-serif'] },
      colors: {
        primary: { 50:'#eff6ff',100:'#dbeafe',200:'#bfdbfe',300:'#93c5fd',400:'#60a5fa',500:'#3b82f6',600:'#2563eb',700:'#1d4ed8',800:'#1e40af',900:'#1e3a8a' },
        navy: { 950:'#020617',900:'#0f172a',800:'#1e293b',700:'#334155' },
        accent: { 400:'#fbbf24',500:'#f59e0b' }
      },
      boxShadow: {
        card: '0 10px 30px -12px rgba(15,23,42,.18)',
        glow: '0 0 0 1px rgba(59,130,246,.15), 0 12px 30px -12px rgba(37,99,235,.35)'
      },
      backgroundImage: {
        'hero-mesh': 'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(59,130,246,.35), transparent), radial-gradient(ellipse 60% 40% at 90% 10%, rgba(245,158,11,.12), transparent)'
      }
    }
  },
  plugins: [],
}
