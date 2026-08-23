/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#FAF9F6',
        surface: '#FFFFFF',
        raised: '#F4F2ED',
        line: '#E4E0D8',
        'line-strong': '#D3CEC3',
        ink: '#1B1A17',
        'ink-2': '#4A4740',
        'ink-3': '#7A756B',
        accent: '#2F5D4A',
        'accent-soft': '#EAF0EB',
        positive: '#3D7A5A',
        'positive-soft': '#E9F1EB',
        caution: '#96662A',
        'caution-soft': '#F6EEE1',
        critical: '#9B4436',
        'critical-soft': '#F7EAE7',
        info: '#3A5A73',
        'info-soft': '#EAEFF3',
      },
      fontFamily: {
        sans: ['"Inter"', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      letterSpacing: {
        label: '0.08em',
      },
      boxShadow: {
        card: '0 1px 2px rgba(27, 26, 23, 0.04)',
        panel: '0 12px 32px -12px rgba(27, 26, 23, 0.18)',
      },
    },
  },
  plugins: [],
}
