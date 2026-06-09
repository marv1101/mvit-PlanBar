import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Button } from './ui/button';
import { Alert, AlertDescription } from './ui/alert';
import { Loader2, PlusCircle, MinusCircle } from 'lucide-react';

interface AdjustBalanceDialogProps {
  employeeId: number;
  employeeName: string;
  currentBalance: number;
  onClose: () => void;
  onSaved: () => void;
}

export function AdjustBalanceDialog({ employeeId, employeeName, currentBalance, onClose, onSaved }: AdjustBalanceDialogProps) {
  const [deltaHours, setDeltaHours] = useState('');
  const [reason, setReason] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const delta = parseFloat(deltaHours);
    if (isNaN(delta) || delta === 0) {
      setError('Bitte geben Sie einen gültigen Stundenwert ein (ungleich 0)');
      return;
    }

    setIsLoading(true);
    try {
      const { adjustTimeAccount } = await import('../services/employeeService');
      await adjustTimeAccount(employeeId, { delta_hours: delta, reason: reason || undefined });
      onSaved();
    } catch {
      setError('Fehler beim Speichern der Korrektur');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div onClick={e => e.stopPropagation()}>
        <Card className="w-full max-w-md mx-4">
          <CardHeader className="space-y-1 text-center">
            <div className="flex justify-center mb-4">
              <div className="bg-amber-600 p-3 rounded-full">
                {deltaHours.startsWith('-') ? (
                  <MinusCircle className="h-8 w-8 text-white" />
                ) : (
                  <PlusCircle className="h-8 w-8 text-white" />
                )}
              </div>
            </div>
            <CardTitle className="text-2xl">Zeitkonto korrigieren</CardTitle>
            <CardDescription>
              {employeeName} &mdash; Aktueller Saldo: {currentBalance > 0 ? '+' : ''}{currentBalance.toFixed(1)}h
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="delta-hours">Korrektur (Stunden)</Label>
                <Input
                  id="delta-hours"
                  type="number"
                  step="0.5"
                  placeholder="z. B. 5.0 oder -3.5"
                  value={deltaHours}
                  onChange={(e) => setDeltaHours(e.target.value)}
                  required
                  disabled={isLoading}
                />
                <p className="text-xs text-gray-500">
                  Positiver Wert = Stunden gutschreiben, negativer Wert = Stunden abziehen
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="reason">Grund (optional)</Label>
                <Input
                  id="reason"
                  type="text"
                  placeholder="z. B. Korrektur Überstunden"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  disabled={isLoading}
                />
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="flex gap-3">
                <Button type="button" variant="outline" className="flex-1" onClick={onClose} disabled={isLoading}>
                  Abbrechen
                </Button>
                <Button type="submit" className="flex-1" disabled={isLoading}>
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Speichern...
                    </>
                  ) : (
                    'Speichern'
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
