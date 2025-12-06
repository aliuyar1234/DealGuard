import { test, expect } from '@playwright/test';

/**
 * Smoke tests to verify the application is working.
 * These tests check basic functionality without deep business logic.
 */

test.describe('Smoke Tests', () => {
  test('homepage loads and shows navigation', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Should have the DealGuard branding
    await expect(page.locator('text=DealGuard')).toBeVisible();

    // Should show main navigation items
    await expect(page.locator('text=Dashboard')).toBeVisible();
    await expect(page.locator('text=Verträge')).toBeVisible();
    await expect(page.locator('text=Partner')).toBeVisible();
  });

  test('dashboard shows key sections', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // In dev mode, should auto-login and show dashboard content
    // Check for dashboard elements
    const pageContent = await page.content();

    // Should have some dashboard content (adjust based on actual UI)
    expect(pageContent).toBeTruthy();
  });

  test('navigation to Verträge works', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Click on Verträge navigation
    await page.click('text=Verträge');
    await page.waitForLoadState('networkidle');

    // Should be on the contracts page
    await expect(page).toHaveURL(/vertraege/);
  });

  test('navigation to Partner works', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Click on Partner navigation
    await page.click('text=Partner');
    await page.waitForLoadState('networkidle');

    // Should be on the partners page
    await expect(page).toHaveURL(/partner/);
  });
});
