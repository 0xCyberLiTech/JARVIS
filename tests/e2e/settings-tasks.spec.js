import { test, expect } from '@playwright/test';

async function dismissOverlays(page) {
  await page.addStyleTag({
    content: `#welcome-modal,#init-cover{display:none!important;visibility:hidden!important;pointer-events:none!important}`,
  });
}

test.describe('JARVIS · Settings / Tâches tabs', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    await dismissOverlays(page);
  });

  test('SETTINGS tab loads facts list and prompt profile badge', async ({ page }) => {
    await page.locator('.tabs .tab', { hasText: 'SETTINGS' }).click();
    await page.waitForTimeout(1500); // _jTabSettings fetches multiple endpoints
    await expect(page.locator('#tab-settings')).toBeVisible();
    await expect(page.locator('#facts-list')).toBeAttached();
    await expect(page.locator('#active-prompt-profile-badge')).toBeAttached();
  });

  test('TÂCHES tab loads task list container and creation form', async ({ page }) => {
    await page.locator('.tabs .tab', { hasText: 'TÂCHES' }).click();
    await page.waitForTimeout(800);
    await expect(page.locator('#tab-taches')).toBeVisible();
    await expect(page.locator('#taches-list')).toBeAttached();
    await expect(page.locator('#task-new-cmd')).toBeAttached();
    await expect(page.locator('#task-new-name')).toBeAttached();
  });

});
