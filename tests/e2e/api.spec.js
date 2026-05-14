import { test, expect } from '@playwright/test';

test.describe('JARVIS · API health', () => {

  test('/api/health returns ok with model + ts', async ({ request }) => {
    const res = await request.get('/api/health');
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBe('ok');
    expect(body.model).toBeTruthy();
    expect(body.ts).toMatch(/\d{4}-\d{2}-\d{2}T/);
  });

  test('/api/mode GET returns current mode + model', async ({ request }) => {
    const res = await request.get('/api/mode');
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(['soc', 'general', 'code', 'code_reasoning']).toContain(body.mode);
    expect(body.model).toBeTruthy();
  });

  test('mode cycle soc→general→soc keeps consistent state', async ({ request }) => {
    const initial = await (await request.get('/api/mode')).json();
    const initMode = initial.mode;

    const r1 = await request.post('/api/mode', { data: { mode: 'general' } });
    expect(r1.status()).toBe(200);
    const b1 = await r1.json();
    expect(b1.mode).toBe('general');

    const r2 = await request.post('/api/mode', { data: { mode: initMode } });
    expect(r2.status()).toBe(200);
    const b2 = await r2.json();
    expect(b2.mode).toBe(initMode);
  });

});
