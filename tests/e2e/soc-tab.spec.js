import { test, expect } from '@playwright/test';

async function dismissOverlays(page) {
  await page.addStyleTag({
    content: `#welcome-modal,#init-cover{display:none!important;visibility:hidden!important;pointer-events:none!important}`,
  });
}

test.describe('JARVIS · SOC tab', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    await dismissOverlays(page);
  });

  test('SOC tab opens and shows counters', async ({ page }) => {
    await page.locator('.tabs .tab', { hasText: 'SOC' }).click();
    await page.waitForTimeout(800);
    await expect(page.locator('#tab-soc')).toBeVisible();
    // 4 compteurs SOC clés présents (ban, fail, ok, ids)
    await expect(page.locator('#soc-cnt-ban')).toBeAttached();
    await expect(page.locator('#soc-cnt-fail')).toBeAttached();
    await expect(page.locator('#soc-cnt-ok')).toBeAttached();
    await expect(page.locator('#soc-cnt-ids')).toBeAttached();
  });

  test('SOC actions list container is rendered', async ({ page }) => {
    await page.locator('.tabs .tab', { hasText: 'SOC' }).click();
    await page.waitForTimeout(800);
    await expect(page.locator('#soc-actions-list')).toBeAttached();
    await expect(page.locator('#soc-chart-day')).toBeAttached();
  });

});
