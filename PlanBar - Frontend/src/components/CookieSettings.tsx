import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/app/components/ui/dialog'
import { Button } from '@/app/components/ui/button'
import { Switch } from '@/app/components/ui/switch'
import { Label } from '@/app/components/ui/label'
import type { CookieConsentData } from '@/lib/cookie-consent'

interface CookieSettingsProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  currentConsent: CookieConsentData
  onSave: (functional: boolean, analytics: boolean) => void
}

export function CookieSettings({
  open,
  onOpenChange,
  currentConsent,
  onSave,
}: CookieSettingsProps) {
  const [functional, setFunctional] = useState(currentConsent.functional)
  const [analytics, setAnalytics] = useState(currentConsent.analytics)

  const handleSave = () => {
    onSave(functional, analytics)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Cookie-Einstellungen</DialogTitle>
          <DialogDescription>
            Verwalten Sie Ihre Cookie-Einstellungen. Notwendige Cookies können nicht deaktiviert werden.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Necessary cookies - always on */}
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label className="text-sm font-medium">Notwendige Cookies</Label>
              <p className="text-xs text-muted-foreground">
                Erforderlich für die Anmeldung und Grundfunktionen. Können nicht deaktiviert werden.
              </p>
            </div>
            <Switch checked disabled />
          </div>

          {/* Functional cookies */}
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label className="text-sm font-medium">Funktionale Cookies</Label>
              <p className="text-xs text-muted-foreground">
                Verbessern die Funktionalität und Personalisierung.
              </p>
            </div>
            <Switch
              checked={functional}
              onCheckedChange={setFunctional}
              aria-label="Funktionale Cookies"
            />
          </div>

          {/* Analytics cookies */}
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label className="text-sm font-medium">Analyse-Cookies</Label>
              <p className="text-xs text-muted-foreground">
                Helfen uns zu verstehen, wie die Seite genutzt wird.
              </p>
            </div>
            <Switch
              checked={analytics}
              onCheckedChange={setAnalytics}
              aria-label="Analyse-Cookies"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Abbrechen
          </Button>
          <Button onClick={handleSave}>
            Speichern
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
