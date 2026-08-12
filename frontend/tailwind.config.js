/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50:  'hsl(255, 100%, 97%)',
          100: 'hsl(255, 100%, 93%)',
          200: 'hsl(255, 95%, 86%)',
          300: 'hsl(255, 90%, 76%)',
          400: 'hsl(255, 85%, 65%)',
          500: 'hsl(255, 80%, 55%)',
          600: 'hsl(255, 75%, 45%)',
          700: 'hsl(255, 70%, 36%)',
          800: 'hsl(255, 65%, 28%)',
          900: 'hsl(255, 60%, 20%)',
        },
        surface: {
          50:  'hsl(230, 20%, 98%)',
          100: 'hsl(230, 18%, 94%)',
          200: 'hsl(230, 16%, 88%)',
          300: 'hsl(230, 14%, 78%)',
          400: 'hsl(230, 12%, 62%)',
          500: 'hsl(230, 10%, 46%)',
          600: 'hsl(230, 12%, 32%)',
          700: 'hsl(230, 14%, 22%)',
          800: 'hsl(230, 16%, 14%)',
          900: 'hsl(230, 18%, 9%)',
          950: 'hsl(230, 20%, 6%)',
        },
        accent: {
          cyan:   'hsl(185, 100%, 55%)',
          purple: 'hsl(280, 100%, 65%)',
          pink:   'hsl(330, 100%, 65%)',
          gold:   'hsl(42,  100%, 60%)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'fade-in':      'fadeIn 0.3s ease-out',
        'slide-up':     'slideUp 0.3s ease-out',
        'slide-in-right': 'slideInRight 0.3s ease-out',
        'pulse-slow':   'pulse 3s ease-in-out infinite',
        'shimmer':      'shimmer 1.5s ease-in-out infinite',
        'typing':       'typing 1.2s ease-in-out infinite',
        'float':        'float 3s ease-in-out infinite',
        'glow':         'glow 2s ease-in-out infinite alternate',
        'spin-slow':    'spin 8s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%':   { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)',    opacity: '1' },
        },
        slideInRight: {
          '0%':   { transform: 'translateX(20px)', opacity: '0' },
          '100%': { transform: 'translateX(0)',    opacity: '1' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0'  },
        },
        typing: {
          '0%, 100%': { opacity: '0.2', transform: 'scale(0.8)' },
          '50%':      { opacity: '1',   transform: 'scale(1.2)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%':      { transform: 'translateY(-8px)' },
        },
        glow: {
          '0%':   { boxShadow: '0 0 5px hsl(255,80%,55%,0.3)' },
          '100%': { boxShadow: '0 0 20px hsl(255,80%,55%,0.7)' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
};
