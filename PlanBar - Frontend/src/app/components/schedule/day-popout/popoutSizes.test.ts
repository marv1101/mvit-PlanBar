import { describe, it, expect } from 'vitest';
import { computePopoutSizes, barTextClass } from './popoutSizes';

describe('computePopoutSizes', () => {
  it('liefert Standardgrößen bei fehlenden Messwerten', () => {
    expect(computePopoutSizes(0, 0, 2)).toEqual({ hourWidth: 96, rowHeight: 56, barHeight: 36 });
  });

  it('streckt die Stundenbreite auf die gefüllte Breite des Bildschirms', () => {
    const sizes = computePopoutSizes(1900, 900, 2);
    expect(sizes.hourWidth).toBeGreaterThanOrEqual(96);
    expect(sizes.hourWidth).toBe(Math.floor((1900 - 160) / 16));
  });

  it('füllt die Dialoghöhe komplett verteilt auf die Mitarbeiterzeilen', () => {
    const sizes = computePopoutSizes(1900, 900, 2);
    expect(sizes.rowHeight).toBe(Math.floor((900 - 64) / 2));
  });

  it('skaliert die Schichtbalken proportional zur Zeile und füllt diese', () => {
    const sizes = computePopoutSizes(1900, 900, 2);
    expect(sizes.barHeight).toBe(sizes.rowHeight - 16);
    expect(sizes.barHeight).toBeLessThan(sizes.rowHeight);
    expect(sizes.barHeight).toBeGreaterThanOrEqual(36);
  });

  it('skaliert die Balkenhöhe nicht über die Zeilenhöhe', () => {
    const sizes = computePopoutSizes(1900, 900, 6);
    expect(sizes.barHeight).toBeLessThan(sizes.rowHeight);
  });

  it('respektiert die Mindesthöhe der Zeile bei vielen Mitarbeitern', () => {
    const sizes = computePopoutSizes(1900, 300, 25);
    expect(sizes.rowHeight).toBe(56);
  });
});

describe('barTextClass', () => {
  it('liefert kompakte Schrift bei kleinen Balken', () => {
    expect(barTextClass(36)).toBe('text-[10px]');
    expect(barTextClass(55)).toBe('text-[10px]');
  });

  it('liefert mittlere Schrift bei mittleren Balken', () => {
    expect(barTextClass(56)).toBe('text-xs');
    expect(barTextClass(87)).toBe('text-xs');
  });

  it('liefert große Schrift bei gezoomten Balken', () => {
    expect(barTextClass(88)).toBe('text-sm');
    expect(barTextClass(300)).toBe('text-sm');
  });
});
