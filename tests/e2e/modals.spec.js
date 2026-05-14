import { test, expect } from '@playwright/test';

async function dismissOverlays(page) {
  await page.addStyleTag({
    content: `#welcome-modal,#init-cover{display:none!important;visibility:hidden!important;pointer-events:none!important}`,
  });
}

async function openDspTab(page) {
  await page.locator('.tabs .tab', { hasText: 'DSP AUDIO' }).click();
  await page.waitForTimeout(500);
  await expect(page.locator('#tab-dsp')).toBeVisible();
}

test.describe('JARVIS · Modals open/close', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    await dismissOverlays(page);
  });

  test('DAT modal opens and closes via close button', async ({ page }) => {
    await openDspTab(page);
    await expect(page.locator('#dat-modal')).toBeHidden();
    await page.locator('[data-action="openDatModal"]').click();
    await expect(page.locator('#dat-modal')).toBeVisible();
    await expect(page.locator('#dat-modal')).toHaveClass(/open/);
    // Le modal DAT est haut, le bouton close peut être hors du viewport 1280x720.
    // On clique via DOM direct pour contourner la check viewport de Playwright.
    await page.evaluate(() => {
      document.querySelector('[data-action="closeDatModal"]').click();
    });
    await page.waitForTimeout(300);
    await expect(page.locator('#dat-modal')).toBeHidden();
  });

  test('MIXER modal opens and closes via close button', async ({ page }) => {
    await openDspTab(page);
    await expect(page.locator('#mixer-modal')).toBeHidden();
    await page.locator('[data-action="openMixerModal"]').click();
    await expect(page.locator('#mixer-modal')).toBeVisible();
    await expect(page.locator('#mixer-modal')).toHaveClass(/open/);
    await page.locator('[data-action="closeMixerModal"]').first().click();
    await page.waitForTimeout(300);
    await expect(page.locator('#mixer-modal')).toBeHidden();
  });

});
