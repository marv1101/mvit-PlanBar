import { describe, it, expect } from 'vitest';
import { getWeekType } from '../week';

describe('getWeekType', () => {
  it('REFERENCE_DATE (1. Januar 2024, Montag) ist Woche A', () => {
    const date = new Date(Date.UTC(2024, 0, 1));
    expect(date.getUTCDay()).toBe(1);
    expect(getWeekType(date)).toBe('A');
  });

  it('7. Januar 2024 (Sonntag) ist Woche A – gleiche Woche wie Montag', () => {
    expect(getWeekType(new Date(Date.UTC(2024, 0, 7)))).toBe('A');
  });

  it('8. Januar 2024 (Montag) ist Woche B – erste volle Grenze', () => {
    expect(getWeekType(new Date(Date.UTC(2024, 0, 8)))).toBe('B');
  });

  it('14. Januar 2024 (Sonntag) ist Woche B', () => {
    expect(getWeekType(new Date(Date.UTC(2024, 0, 14)))).toBe('B');
  });

  it('15. Januar 2024 (Montag) ist Woche A', () => {
    expect(getWeekType(new Date(Date.UTC(2024, 0, 15)))).toBe('A');
  });

  it('Montag und Sonntag derselben Woche haben denselben WeekType', () => {
    const monday = new Date(Date.UTC(2024, 2, 4));
    const sunday = new Date(Date.UTC(2024, 2, 10));
    expect(getWeekType(monday)).toBe(getWeekType(sunday));
  });

  it('31. Dezember 2024 (Dienstag) – Jahrgrenze, Woche A (gleiche Woche wie 30.12.)', () => {
    expect(getWeekType(new Date(Date.UTC(2024, 11, 31)))).toBe('A');
  });

  it('1. Januar 2025 (Mittwoch) – Jahrgrenze, Woche A (gleiche Woche wie 30.12.2024)', () => {
    expect(getWeekType(new Date(Date.UTC(2025, 0, 1)))).toBe('A');
  });

  it('6. Januar 2025 (Montag) ist Woche B', () => {
    expect(getWeekType(new Date(Date.UTC(2025, 0, 6)))).toBe('B');
  });
});
