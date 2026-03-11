/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#F0F2F8',
          secondary: '#FFFFFF',
          tertiary: '#E8EBF3',
          card: '#FFFFFF',
          sidebar: '#FFFFFF',
        },
        border: {
          DEFAULT: '#E2E6F0',
          light: '#EDF0F7',
          focus: '#4A7BF7',
        },
        accent: {
          blue: '#4A7BF7',
          'blue-light': '#EBF0FF',
          cyan: '#06B6D4',
          purple: '#8B5CF6',
          green: '#22C55E',
          red: '#EF4444',
          amber: '#F59E0B',
        },
        text: {
          primary: '#1E293B',
          secondary: '#64748B',
          muted: '#94A3B8',
          heading: '#0F172A',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)',
        'card-lg': '0 4px 16px rgba(0, 0, 0, 0.08)',
        'button': '0 2px 8px rgba(74, 123, 247, 0.25)',
        'input': '0 2px 12px rgba(0, 0, 0, 0.04)',
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'fade-in': 'fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'slide-up': 'slideUp 0.3s ease-out',
        'float': 'float 6s ease-in-out infinite',
        'network-pulse': 'networkPulse 3s ease-in-out infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        networkPulse: {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '0.8' },
        },
      },
    },
  },
  plugins: [],
}
