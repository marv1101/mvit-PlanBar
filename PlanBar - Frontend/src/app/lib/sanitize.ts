const MAX_LABEL_LENGTH = 100;

const SCRIPT_TAG_RE = /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi;
const HTML_TAG_RE = /<[^>]*>/g;

export function sanitizeLabel(input: string): string {
  let s = input.trim();
  s = s.replace(SCRIPT_TAG_RE, '');
  s = s.replace(HTML_TAG_RE, '');
  s = s.slice(0, MAX_LABEL_LENGTH);
  return s;
}
