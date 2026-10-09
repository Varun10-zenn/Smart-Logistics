/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        serif: ['Newsreader', 'Georgia', 'serif'],
        sans: ['Instrument Sans', 'system-ui', 'sans-serif'],
      },
      colors: {
        surface: {
          DEFAULT: '#1B2027',
          2: '#232932',
          3: '#2D343E',
        },
        ink: {
          DEFAULT: '#E7EAEE',
          mute: '#98A1AD',
        },
        line: '#2D343E',
        status: {
          ok: '#4F6B5A',
          'ok-text': '#88A594',
          warn: '#8A6A34',
          'warn-text': '#C0A063',
          critical: '#8C4A47',
          'critical-text': '#C58783',
          info: '#4A6078',
          'info-text': '#8FA6BE',
        },
      },
      backgroundImage: {
        'grad-lead': 'linear-gradient(135deg, #4A5563, #2C333D)',
        'grad-side': 'linear-gradient(180deg, #20252C, #14171C)',
        'grad-page': 'linear-gradient(160deg, #0F1216, #181C22)',
        'grad-inset': 'linear-gradient(160deg, #1B2027, #232932)',
      },
      borderRadius: {
        frame: '18px',
        card: '14px',
        input: '10px',
        btn: '9px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(20,23,28,.06), 0 12px 32px -12px rgba(20,23,28,.18)',
        'card-hover': '0 1px 2px rgba(20,23,28,.08), 0 16px 40px -12px rgba(20,23,28,.28)',
      },
    },
  },
  plugins: [],
};
