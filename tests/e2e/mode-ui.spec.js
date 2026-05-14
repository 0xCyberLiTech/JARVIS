import { test, expect } from '@playwright/test';

async function dismissOverlays(page) {
  await page.addStyleTag({
    content: `#welcome-modal,#init-cover{display:none!important;visibility:hidden!important;pointer-events:none!important}`,
  });
}

test.describe('JARVIS · Mode switch via UI buttons', () => {

  test('clicking GEN then SOC button propagates to /api/mode (UI ↔ backend)', async ({ page, request }) => {
    // Snapshot mode initial pour restaurer en fin de test
    const initial = await (await request.get('/api/mode')).json();
    const initMode = initial.mode;

    await page.goto('/');
    await page.waitForTimeout(1000);
    await dismissOverlays(page);

    // 4 boutons mode présents
    await expect(page.locator('#btn-mode-soc')).toBeAttached();
    await expect(page.locator('#btn-mode-general')).toBeAttached();
    await expect(page.locator('#btn-mode-code')).toBeAttached();
    await expect(page.locator('#btn-mode-code-reasoning')).toBeAttached();

    // Click GEN button → vérifier propagation API
    await page.locator('#btn-mode-general').click();
    await page.waitForTimeout(1000);
    const afterGen = await (await request.get('/api/mode')).json();
    expect(afterGen.mode).toBe('general');

    // Restauration : click SOC pour ne pas laisser le mode en GEN
    await page.locator('#btn-mode-soc').click();
    await page.waitForTimeout(1000);
    const afterSoc = await (await request.get('/api/mode')).json();
    expect(afterSoc.mode).toBe('soc');

    // Si initMode était autre chose que soc, restauration finale via API
    if (initMode !== 'soc') {
      await request.post('/api/mode', { data: { mode: initMode } });
    }
  });

});
