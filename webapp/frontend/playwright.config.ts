import { defineConfig } from '@playwright/test'

// End-to-end acceptance tests against the production build served by `vite preview`.
// Without a running API the app reads the versioned API snapshot, whose responses are identical.
// Locally (Windows) the installed Chrome is used with PW_CHANNEL=chrome; CI installs Chromium.
export default defineConfig({
  testDir: 'e2e',
  timeout: 60_000,
  use: {
    baseURL: 'http://127.0.0.1:4174',
    channel: process.env.PW_CHANNEL || undefined,
    viewport: { width: 1440, height: 1000 },
  },
  webServer: {
    command: 'npm run build && npx vite preview --host 127.0.0.1 --port 4174 --strictPort',
    url: 'http://127.0.0.1:4174',
    reuseExistingServer: false,
    timeout: 120_000,
  },
})
