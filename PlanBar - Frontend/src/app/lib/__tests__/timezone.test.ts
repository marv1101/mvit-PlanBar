import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('TIMEZONE', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
  });

  it('verwendet Intl.DateTimeFormat-Fallback wenn VITE_TIMEZONE nicht gesetzt', async () => {
    const expected = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const { TIMEZONE } = await import('../timezone');
    expect(TIMEZONE).toBe(expected);
  });

  it('verwendet VITE_TIMEZONE aus der Umgebungsvariable', async () => {
    vi.stubEnv('VITE_TIMEZONE', 'Europe/Berlin');
    const mod = await import('../timezone');
    expect(mod.TIMEZONE).toBe('Europe/Berlin');
  });

  it('verwendet Intl.DateTimeFormat-Fallback bei leerem VITE_TIMEZONE', async () => {
    vi.stubEnv('VITE_TIMEZONE', '');
    const expected = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const { TIMEZONE } = await import('../timezone');
    expect(TIMEZONE).toBe(expected);
  });
});
