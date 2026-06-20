import { describe, it, expect } from 'vitest';
import { sanitizeLabel } from '../sanitize';

describe('sanitizeLabel', () => {
  it('entfernt <script>-Tags', () => {
    const input = 'Hallo <script>alert("xss")</script> Welt';
    expect(sanitizeLabel(input)).toBe('Hallo  Welt');
  });

  it('entfernt <script>-Tags mit Attributen', () => {
    const input = '<script type="text/javascript">böse</script>Text';
    expect(sanitizeLabel(input)).toBe('Text');
  });

  it('entfernt alle HTML-Tags', () => {
    const input = '<b>Fett</b> und <i>kursiv</i>';
    expect(sanitizeLabel(input)).toBe('Fett und kursiv');
  });

  it('kürzt auf maximal 100 Zeichen', () => {
    const input = 'A'.repeat(150);
    const result = sanitizeLabel(input);
    expect(result).toHaveLength(100);
  });

  it('schneidet Whitespace vorne und hinten ab', () => {
    const input = '  Hallo Welt  ';
    expect(sanitizeLabel(input)).toBe('Hallo Welt');
  });

  it('kürzt nach dem Trimmen auf 100 Zeichen', () => {
    const input = '  ' + 'B'.repeat(200);
    const result = sanitizeLabel(input);
    expect(result).toHaveLength(100);
    expect(result).toBe('B'.repeat(100));
  });

  it('gibt leeren String für leere Eingabe zurück', () => {
    expect(sanitizeLabel('')).toBe('');
  });

  it('lässt bereits sauberen String unverändert', () => {
    const input = 'Sicherer Text ohne HTML';
    expect(sanitizeLabel(input)).toBe('Sicherer Text ohne HTML');
  });

  it('entfernt verschachtelte HTML-Tags', () => {
    const input = '<div><span>tief</span></div>verschachtelt';
    expect(sanitizeLabel(input)).toBe('tiefverschachtelt');
  });
});
