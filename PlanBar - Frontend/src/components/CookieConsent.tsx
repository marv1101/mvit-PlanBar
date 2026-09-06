import { useState, useEffect } from 'react'
import { Button } from '@/app/components/ui/button'
import { CookieSettings } from './CookieSettings'
import { getConsent, acceptAll, acceptNecessaryOnly, saveCustomConsent } from '@/lib/cookie-consent'
import type { CookieConsentData } from '@/lib/cookie-consent'

export function CookieConsent() {
  const [consent, setConsent] = useState<CookieConsentData | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [showBanner, setShowBanner] = useState(false)

  useEffect(() => {
    const existing = getConsent()
    setConsent(existing)
    setShowBanner(existing === null)
  }, [])

  const handleAcceptAll = () => {
    const newConsent = acceptAll()
    setConsent(newConsent)
    setShowBanner(false)
  }

  const handleAcceptNecessary = () => {
    const newConsent = acceptNecessaryOnly()
    setConsent(newConsent)
    setShowBanner(false)
  }

  const handleSaveSettings = (functional: boolean, analytics: boolean) => {
    const newConsent = saveCustomConsent(functional, analytics)
    setConsent(newConsent)
    setShowBanner(false)
  }

  const handleOpenSettings = () => {
    setShowSettings(true)
  }

  // Always render the settings link (footer), even when banner is hidden
  const settingsLink = (
    <button
      onClick={handleOpenSettings}
      className="text-xs text-muted-foreground underline hover:text-foreground transition-colors"
      data-testid="cookie-settings-link"
    >
      Cookie-Einstellungen
    </button>
  )

  if (!showBanner) {
    return (
      <>
        {settingsLink}
        <CookieSettings
          open={showSettings}
          onOpenChange={setShowSettings}
          currentConsent={consent || { necessary: true, functional: false, analytics: false }}
          onSave={handleSaveSettings}
        />
      </>
    )
  }

  return (
    <>
      <div
        className="fixed bottom-0 left-0 right-0 z-50 bg-background border-t p-4 shadow-lg"
        role="dialog"
        aria-label="Cookie-Einwilligung"
        data-testid="cookie-banner"
      >
        <div className="container mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="max-w-2xl">
            <h2 className="text-lg font-semibold mb-1">Cookie-Einwilligung</h2>
            <p className="text-sm text-muted-foreground">
              Wir verwenden Cookies, um Ihnen die beste Erfahrung zu bieten.
              Notwendige Cookies sind für den Betrieb erforderlich. Weitere Cookies
              können Sie optional aktivieren.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row gap-2 shrink-0">
            <Button variant="outline" onClick={handleAcceptNecessary}>
              Nur Notwendige
            </Button>
            <Button variant="outline" onClick={handleOpenSettings}>
              Einstellungen
            </Button>
            <Button onClick={handleAcceptAll}>
              Alle Akzeptieren
            </Button>
          </div>
        </div>
      </div>

      <CookieSettings
        open={showSettings}
        onOpenChange={setShowSettings}
        currentConsent={consent || { necessary: true, functional: false, analytics: false }}
        onSave={handleSaveSettings}
      />
    </>
  )
}
