export interface CookieConsentData {
  necessary: boolean
  functional: boolean
  analytics: boolean
}

const STORAGE_KEY = 'cookie-consent'

export function getConsent(): CookieConsentData | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return JSON.parse(stored)
    }
  } catch {
    return null
  }
  return null
}

export function setConsent(consent: CookieConsentData): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(consent))
}

export function hasConsent(): boolean {
  return getConsent() !== null
}

export function acceptAll(): CookieConsentData {
  const consent: CookieConsentData = {
    necessary: true,
    functional: true,
    analytics: true,
  }
  setConsent(consent)
  return consent
}

export function acceptNecessaryOnly(): CookieConsentData {
  const consent: CookieConsentData = {
    necessary: true,
    functional: false,
    analytics: false,
  }
  setConsent(consent)
  return consent
}

export function saveCustomConsent(functional: boolean, analytics: boolean): CookieConsentData {
  const consent: CookieConsentData = {
    necessary: true,
    functional,
    analytics,
  }
  setConsent(consent)
  return consent
}
