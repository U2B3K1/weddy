import { defineConfig, devices } from '@playwright/test'

// E2E: alohida baza (weddy_e2e) va alohida portlar — dev muhit (8000/5173, foydalanuvchi bazasi) tegilmaydi.
// Ishga tushirish: `npm run e2e` (Docker'dagi PostgreSQL ishlab turishi kerak; baza yo'q bo'lsa global-setup yaratadi).
const API = 'http://127.0.0.1:8001'
const ILOVA = 'http://127.0.0.1:5174'
const PYTHON = process.platform === 'win32' ? '.venv\\Scripts\\python.exe' : '.venv/bin/python'
export const E2E_BAZA = 'postgres://weddy:weddy@localhost:5433/weddy_e2e'

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.js',
  workers: 1,  // bitta salon va bitta smena — testlar ketma-ket
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],
  use: {
    baseURL: ILOVA,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    ...devices['Desktop Chrome'],
    viewport: { width: 1280, height: 860 },
  },
  projects: [
    { name: 'qurilma', testMatch: /qurilma\.setup\.js/ },
    { name: 'ilova', dependencies: ['qurilma'], use: { storageState: 'e2e/.qurilma.json' } },
  ],
  webServer: [
    {
      command: `${PYTHON} manage.py runserver 127.0.0.1:8001 --noreload`,
      cwd: '../backend',
      url: `${API}/api/sogliq/`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        DATABASE_URL: E2E_BAZA, DEBUG: 'True', CORS_ALLOWED_ORIGINS: ILOVA,
        THROTTLE_ANON: '10000/min', THROTTLE_USER: '10000/min',
      },
    },
    {
      command: 'npx vite --host 127.0.0.1 --port 5174 --strictPort',
      url: ILOVA,
      reuseExistingServer: false,
      timeout: 120_000,
      env: { VITE_API_URL: `${API}/api` },
    },
  ],
})
