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

// Set la valeur d'un slider <input type=range> + déclenche l'event 'input' que le dispatcher écoute.
async function setSlider(page, sliderId, value) {
  await page.evaluate(({ id, v }) => {
    const el = document.getElementById(id);
    el.value = String(v);
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }, { id: sliderId, v: value });
}

test.describe('JARVIS · DSP EQ slider interaction', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    await dismissOverlays(page);
    await openDspTab(page);
  });

  test('EQ low slider updates its label when changed', async ({ page }) => {
    const before = await page.locator('#eq-low-val').textContent();
    expect(before).toMatch(/dB/i);

    await setSlider(page, 'eq-low', 6);
    await page.waitForTimeout(200);

    const after = await page.locator('#eq-low-val').textContent();
    expect(after).toMatch(/6/);
    expect(after).toMatch(/dB/i);

    // Restore à 0 pour ne pas laisser le DSP altéré
    await setSlider(page, 'eq-low', 0);
  });

  test('EQ high slider updates its label when changed', async ({ page }) => {
    await setSlider(page, 'eq-high', -4.5);
    await page.waitForTimeout(200);

    const after = await page.locator('#eq-high-val').textContent();
    expect(after).toMatch(/-4\.?5?/);
    expect(after).toMatch(/dB/i);

    await setSlider(page, 'eq-high', 0);
  });

  test('EQ air slider responds to value change', async ({ page }) => {
    await setSlider(page, 'eq-air', 3);
    await page.waitForTimeout(200);

    const after = await page.locator('#eq-air-val').textContent();
    expect(after).toMatch(/3/);

    await setSlider(page, 'eq-air', 0);
  });

});
