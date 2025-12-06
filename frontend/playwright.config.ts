import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E Test Configuration for DealGuard Frontend
 *
 * Run tests:
 *   npm run test:e2e           - Run all E2E tests headlessly
 *   npm run test:e2e:ui        - Open Playwright UI for debugging
 *   npm run test:e2e:headed    - Run tests with visible browser
 *
 * See .claude/skills/webapp-testing/SKILL.md for testing patterns.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    // Optionally add more browsers
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  // Run local dev server before tests
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
