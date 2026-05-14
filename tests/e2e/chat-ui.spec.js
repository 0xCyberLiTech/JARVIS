import { test, expect } from '@playwright/test';

async function dismissOverlays(page) {
  await page.addStyleTag({
    content: `#welcome-modal,#init-cover{display:none!important;visibility:hidden!important;pointer-events:none!important}`,
  });
}

test.describe('JARVIS · Chat UI', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(800);
    await dismissOverlays(page);
  });

  test('chat tab is active by default', async ({ page }) => {
    const active = await page.locator('.tabs .tab.active').textContent();
    expect(active).toMatch(/JARVIS AI/i);
  });

  test('chat input field exists and is editable', async ({ page }) => {
    const input = page.locator('#user-input');
    await expect(input).toBeVisible({ timeout: 5000 });
    await input.click();
    await input.fill('test e2e');
    await expect(input).toHaveValue('test e2e');
    await input.fill('');
  });

});
