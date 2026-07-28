import { defineConfig } from '@playwright/test'
import { fileURLToPath, URL } from 'node:url'

const frontendDir = fileURLToPath(new URL('.', import.meta.url))
const e2eDatabase = fileURLToPath(
  new URL('../backend/e2e.sqlite3', import.meta.url),
)

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45_000,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  globalSetup: './e2e/global-setup.ts',
  outputDir: 'test-results',
  use: {
    baseURL: 'http://127.0.0.1:15173',
    channel: 'chrome',
    headless: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: [
    {
      command:
        'uv run --project ../backend python ../backend/manage.py runserver 127.0.0.1:18000 --noreload --settings=config.settings.test',
      cwd: frontendDir,
      env: {
        DJANGO_SETTINGS_MODULE: 'config.settings.test',
        SQLITE_TEST_DB: e2eDatabase,
      },
      url: 'http://127.0.0.1:18000/health/live',
      timeout: 60_000,
      reuseExistingServer: false,
    },
    {
      command: 'pnpm dev --host 127.0.0.1 --port 15173',
      cwd: frontendDir,
      env: {
        VITE_DEV_PROXY_TARGET: 'http://127.0.0.1:18000',
      },
      url: 'http://127.0.0.1:15173/login',
      timeout: 60_000,
      reuseExistingServer: false,
    },
  ],
})
