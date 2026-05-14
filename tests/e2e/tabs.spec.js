import { test, expect } from '@playwright/test';

async function dismissOverlays(page) {
  await page.addStyleTag({
    content: `#welcome-modal,#init-cover{display:none!important;visibility:hidden!important;pointer-events:none!important}`,
  });
}

test.describe('JARVIS · Tabs navigation', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(800);
    await dismissOverlays(page);
  });

  test('Monitor tab is reachable', async ({ page }) => {
    await page.locator('.tabs .tab', { hasText: 'Monitor' }).click();
    await page.waitForTimeout(300);
    const active = await page.locator('.tabs .tab.active').textContent();
    expect(active).toMatch(/Monitor/i);
  });

  test('SETTINGS tab opens', async ({ page }) => {
    await page.locator('.tabs .tab', { hasText: 'SETTINGS' }).click();
    await page.waitForTimeout(500);
    const active = await page.locator('.tabs .tab.active').textContent();
    expect(active).toMatch(/SETTINGS/i);
  });

  test('DSP AUDIO tab opens', async ({ page }) => {
    await page.locator('.tabs .tab', { hasText: 'DSP AUDIO' }).click();
    await page.waitForTimeout(500);
    const active = await page.locator('.tabs .tab.active').textContent();
    expect(active).toMatch(/DSP AUDIO/i);
  });

});
