import { test, expect } from '@playwright/test';

test.describe('JARVIS · Boot', () => {

  test('page loads without console errors', async ({ page }) => {
    const errors = [];
    page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const txt = msg.text();
        if (!/favicon|net::ERR_|Failed to load resource/i.test(txt)) {
          errors.push(`console.error: ${txt}`);
        }
      }
    });

    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('.logo')).toBeVisible();
    await expect(page.locator('.status-live')).toContainText(/SYSTEM ONLINE/i);
    await page.waitForTimeout(1500);
    expect(errors, `console/page errors: ${errors.join(' | ')}`).toEqual([]);
  });

  test('header tabs are all rendered', async ({ page }) => {
    await page.goto('/');
    const tabs = page.locator('.tabs .tab');
    await expect(tabs).toHaveCount(7);
    await expect(tabs.nth(0)).toContainText(/Monitor/i);
    await expect(tabs.nth(1)).toContainText(/JARVIS AI/i);
    await expect(tabs.nth(2)).toContainText(/SETTINGS/i);
    await expect(tabs.nth(3)).toContainText(/DSP AUDIO/i);
    await expect(tabs.nth(6)).toContainText(/SOC/i);
  });

});
