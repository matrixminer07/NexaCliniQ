import daisyui from 'daisyui'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Space Grotesk', 'Segoe UI', 'sans-serif'],
        body: ['Manrope', 'Segoe UI', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      colors: {
        brand: {
          DEFAULT: '#6366f1',
          dim: '#4f46e5',
          glow: 'rgba(99,102,241,0.22)',
          subtle: 'rgba(99,102,241,0.16)',
        },
        surface: {
          base: '#0f172a',
          1: '#1e293b',
          2: '#233145',
          3: '#2a3a52',
          4: '#324560',
        },
        ink: {
          primary: '#f1f5f9',
          secondary: '#94a3b8',
          tertiary: '#7b8ca4',
          disabled: '#5f738f',
        },
        state: {
          pass: '#22c55e',
          caution: '#f59e0b',
          fail: '#ef4444',
          info: '#60a5fa',
        }
      },
      animation: {
        'fade-up': 'fadeUp 0.4s ease-out forwards',
        'fade-in': 'fadeIn 0.3s ease-out forwards',
        'pulse-ring': 'pulseRing 1.5s ease-out infinite',
        'count-up': 'countUp 0.6s ease-out forwards',
        'dna-spin': 'dnaSpin 1.2s linear infinite',
        'slide-in-r': 'slideInRight 0.3s ease-out forwards',
        'glow-pulse': 'glowPulse 2s ease-in-out infinite',
      },
      keyframes: {
        fadeUp: { from: { opacity:'0', transform:'translateY(20px)' }, to: { opacity:'1', transform:'translateY(0)' } },
        fadeIn: { from: { opacity:'0' }, to: { opacity:'1' } },
        pulseRing: { '0%': { transform:'scale(1)', opacity:'0.8' }, '100%': { transform:'scale(1.4)', opacity:'0' } },
        slideInRight: { from: { transform:'translateX(100%)' }, to: { transform:'translateX(0)' } },
        glowPulse: { '0%,100%': { boxShadow:'0 0 0 0 rgba(0,200,150,0)' }, '50%': { boxShadow:'0 0 20px 4px rgba(0,200,150,0.3)' } },
      },
      boxShadow: {
        'brand-glow': '0 0 20px rgba(0,200,150,0.25)',
        'card': '0 0 0 1px rgba(0,200,150,0.12)',
        'card-hover': '0 0 0 1px rgba(0,200,150,0.35)',
      },
      borderColor: {
        DEFAULT: 'rgba(0,200,150,0.12)',
      }
    }
  },
  plugins: [daisyui],
  daisyui: {
    themes: [
      {
        novacura: {
          primary: '#6366f1',
          secondary: '#22c55e',
          accent: '#4f46e5',
          neutral: '#1F2937',
          'base-100': '#0f172a',
          'base-200': '#1e293b',
          'base-300': '#334155',
          info: '#60a5fa',
          success: '#22c55e',
          warning: '#F59E0B',
          error: '#EF4444',
        },
      },
    ],
  },
}
