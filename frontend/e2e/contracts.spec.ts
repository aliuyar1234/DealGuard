import { expect, test } from '@playwright/test';

/**
 * E2E tests for contract management functionality.
 *
 * Note: These tests assume `NEXT_PUBLIC_AUTH_PROVIDER=dev` is set, which bypasses
 * Supabase auth and uses a mock user/token.
 */

test.describe('Contract Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/vertraege');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/Vertr/i);
  });

  test('contracts list page loads', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/Vertr/i);
    await expect(page.locator('a[href="/vertraege/neu"]')).toBeVisible();
  });

  test('new contract page loads', async ({ page }) => {
    await page.goto('/vertraege/neu');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/Vertrag analysieren/i);
    await expect(page.getByText(/Dokument hochladen/i)).toBeVisible();
  });

  test('contract upload form has required elements', async ({ page }) => {
    await page.goto('/vertraege/neu');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/Vertrag analysieren/i);

    await expect(page.locator('input[type="file"]')).toBeAttached();
    await expect(page.getByRole('button', { name: /Analyse starten/i })).toBeVisible();
  });
});

test.describe('Contract Analysis', () => {
  test.skip('contract upload triggers analysis', async ({ page }) => {
    await page.goto('/vertraege/neu');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/Vertrag analysieren/i);
  });
});

