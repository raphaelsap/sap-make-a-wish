/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'sap-primary': '#0a6ed1',
        'sap-accent': '#2fdf84',
        'glass-foreground': 'rgba(255, 255, 255, 0.8)',
      },
      backgroundImage: {
        'apple-glass': 'linear-gradient(135deg, rgba(15, 23, 42, 0.7), rgba(10, 110, 209, 0.4))',
        'sap-fiori': 'linear-gradient(135deg, rgba(10, 110, 209, 0.75), rgba(47, 223, 132, 0.55))',
      },
      boxShadow: {
        glass: '0 30px 60px -15px rgba(15, 23, 42, 0.6)',
      },
      fontFamily: {
        sap: ['"72"', '"72full"', 'Inter', 'sans-serif'],
      },
      borderRadius: {
        '3xl': '1.75rem',
      },
    },
  },
  plugins: [],
};
