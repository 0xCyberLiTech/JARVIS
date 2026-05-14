import { test, expect } from '@playwright/test';

async function dismissOverlays(page) {
  await page.addStyleTag({
    content: `#welcome-modal,#init-cover{display:none!important;visibility:hidden!important;pointer-events:none!important}`,
  });
}

test.describe('JARVIS · DSP / Voice Lab tabs', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    await dismissOverlays(page);
  });

  test('DSP tab opens and DAT player buttons are present', async ({ page }) => {
    await page.locator('.tabs .tab', { hasText: 'DSP AUDIO' }).click();
    await page.waitForTimeout(800);
    await expect(page.locator('#tab-dsp')).toBeVisible();
    await expect(page.locator('#dat-btn-play')).toBeAttached();
    await expect(page.locator('#dat-btn-pause')).toBeAttached();
    await expect(page.locator('#dat-btn-rec')).toBeAttached();
  });

  test('Voice Lab tab opens and engine selectors are present', async ({ page }) => {
    await page.locator('.tabs .tab', { hasText: 'VOICE LAB' }).click();
    await page.waitForTimeout(800);
    await expect(page.locator('#tab-voicelab')).toBeVisible();
    await expect(page.locator('#vlab-eng-edge')).toBeAttached();
    await expect(page.locator('#vlab-eng-kokoro')).toBeAttached();
    await expect(page.locator('#vlab-eng-piper')).toBeAttached();
    await expect(page.locator('#vlab-eng-sapi')).toBeAttached();
  });

  test('Voice Lab A/B comparison slots present', async ({ page }) => {
    await page.locator('.tabs .tab', { hasText: 'VOICE LAB' }).click();
    await page.waitForTimeout(800);
    await expect(page.locator('#vlab-ab-a')).toBeAttached();
    await expect(page.locator('#vlab-ab-b')).toBeAttached();
  });

});
