export const TIMEZONE: string =
  (import.meta as { env: { VITE_TIMEZONE?: string } }).env.VITE_TIMEZONE ||
  Intl.DateTimeFormat().resolvedOptions().timeZone;
