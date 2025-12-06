import { test, expect } from '@playwright/test';
import path from 'path';

/**
 * E2E tests for contract management functionality.
 *
 * Note: These tests assume AUTH_PROVIDER=dev is set, which auto-logs in users.
 * For production testing, you'd need to handle authentication.
 */

test.describe('Contract Management', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to contracts page before each test
    await page.goto('/vertraege');
    await page.waitForLoadState('networkidle');
  });

  test('contracts list page loads', async ({ page }) => {
    // Should show the contracts list heading
    await expect(page.locator('h1, h2').first()).toBeVisible();

    // Should have a button to add new contract
    const newContractLink = page.locator('a[href="/vertraege/neu"], button:has-text("Neu")');
    await expect(newContractLink.first()).toBeVisible();
  });

  test('new contract page loads', async ({ page }) => {
    await page.goto('/vertraege/neu');
    await page.waitForLoadState('networkidle');

    // Should show upload form
    await expect(page.locator('text=Upload').or(page.locator('text=Hochladen'))).toBeVisible();
  });

  test('contract upload form has required elements', async ({ page }) => {
    await page.goto('/vertraege/neu');
    await page.waitForLoadState('networkidle');

    // Should have file input (may be hidden for styling)
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();

    // Should have a submit button
    const submitButton = page.locator('button[type="submit"], button:has-text("Analysieren")');
    await expect(submitButton.first()).toBeVisible();
  });
});

test.describe('Contract Analysis', () => {
  // These tests would require a running backend
  // Skip if backend is not available

  test.skip('contract upload triggers analysis', async ({ page }) => {
    await page.goto('/vertraege/neu');
    await page.waitForLoadState('networkidle');

    // This test would:
    // 1. Upload a sample PDF
    // 2. Wait for analysis to complete
    // 3. Verify risk score is displayed

    // Example (requires actual test file):
    // const fileInput = page.locator('input[type="file"]');
    // await fileInput.setInputFiles('./fixtures/sample-contract.pdf');
    // await page.click('button:has-text("Analysieren")');
    // await expect(page.locator('text=Risiko-Score')).toBeVisible({ timeout: 60000 });
  });
});
