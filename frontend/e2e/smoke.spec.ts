import { expect, test } from '@playwright/test';

/**
 * Smoke tests to verify the application is working.
 *
 * These tests avoid waiting for `networkidle` because Next.js dev-mode/HMR can
 * keep connections open and cause flaky timeouts.
 */

test.describe('Smoke Tests', () => {
  test('homepage loads and shows navigation', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('link', { name: 'DealGuard' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
    await expect(page.locator('a[href="/vertraege"]')).toBeVisible();
    await expect(page.locator('a[href="/partner"]')).toBeVisible();
  });

  test('dashboard shows key sections', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1, name: /Dashboard/i })).toBeVisible();
    expect(await page.content()).toBeTruthy();
  });

  test('navigation to contracts works', async ({ page }) => {
    await page.goto('/');
    await page.locator('a[href="/vertraege"]').click();

    await expect(page).toHaveURL(/vertraege/);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(/Vertr/i);
  });

  test('navigation to partners works', async ({ page }) => {
    await page.goto('/');
    await page.locator('a[href="/partner"]').click();

    await expect(page).toHaveURL(/partner/);
  });
});
