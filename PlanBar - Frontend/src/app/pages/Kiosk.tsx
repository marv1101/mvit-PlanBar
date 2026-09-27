import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { format } from 'date-fns';
import { de } from 'date-fns/locale';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useKioskBoard } from '../hooks/useKioskBoard';
import { kioskLogin } from '../services/kioskService';
import { KioskBoard } from '../components/kiosk/KioskBoard';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Button } from '../components/ui/button';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Loader2, Lock } from 'lucide-react';

export function Kiosk() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100">
        <div data-testid="kiosk-loading" className="text-center">
          <Loader2 className="h-12 w-12 mx-auto animate-spin text-blue-500" />
        </div>
      </div>
    );
  }

  if (!user) {
    return <KioskLogin />;
  }

  return <KioskDashboard />;
}

function KioskLogin() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await kioskLogin(email, password);
      // Reloading re-probes /users/me via AuthProvider, so the board
      // appears after the auth cookies are set. must_change_password is
      // intentionally ignored on the kiosk page.
      window.location.reload();
      return;
    } catch (err) {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : null;
      const msg = Array.isArray(detail)
        ? detail.map((d) => d.msg).join('; ')
        : detail || 'Anmeldung fehlgeschlagen';
      setError(msg);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
      <div className="w-full max-w-md bg-slate-900 rounded-xl shadow-lg border border-slate-800 p-8">
        <div className="flex flex-col items-center text-center mb-6">
          <div className="bg-blue-600 p-3 rounded-full mb-4">
            <Lock className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-semibold text-slate-100">MVIT PlanBar – Kiosk</h1>
          <p className="mt-2 text-slate-400">
            Bitte melden Sie sich an, um den Dienstplan zu sehen.
          </p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-slate-200">E-Mail</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
              disabled={isLoading}
              className="bg-slate-950 border-slate-700 text-slate-100"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password" className="text-slate-200">Passwort</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              disabled={isLoading}
              className="bg-slate-950 border-slate-700 text-slate-100"
            />
          </div>
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Anmelden...
              </>
            ) : (
              'Anmelden'
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}

function KioskDashboard() {
  const [searchParams] = useSearchParams();
  const teamParam = searchParams.get('team');
  const teamId = teamParam !== null && teamParam !== '' ? Number(teamParam) : null;

  const { data, isLoading, error, dataUpdatedAt, refetch } = useKioskBoard(teamId);

  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(timer);
  }, []);

  const teamName = data?.team?.name ?? 'Alle Kollegen';

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <header className="px-6 py-6 border-b border-slate-800">
        <div className="max-w-[1600px] mx-auto w-full flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <h1 className="text-3xl md:text-4xl font-semibold">Dienstplan</h1>
            <p className="text-xl md:text-2xl text-blue-400 mt-1">{teamName}</p>
          </div>
          <div className="text-right">
            <p className="text-xl md:text-2xl font-medium">
              {format(now, "EEEE, d. MMMM yyyy", { locale: de })}
            </p>
            <p className="text-lg text-slate-400">
              {format(now, 'HH:mm')}
              {dataUpdatedAt > 0 && (
                <span className="ml-4 text-base">
                  Zuletzt aktualisiert: {format(new Date(dataUpdatedAt), 'HH:mm')}
                </span>
              )}
            </p>
          </div>
        </div>
      </header>

      <main className="flex-1 px-4 md:px-6 py-6 max-w-[1600px] mx-auto w-full">
        {isLoading && (
          <div data-testid="kiosk-loading" className="py-16 text-center">
            <Loader2 className="h-10 w-10 mx-auto animate-spin text-blue-500" />
          </div>
        )}
        {!isLoading && error && (
          <div
            data-testid="kiosk-error"
            role="alert"
            className="max-w-lg mx-auto mt-12 rounded-lg border border-red-700 bg-red-950/60 p-6 text-center"
          >
            <p className="text-lg font-medium text-red-300 mb-4">
              Dienstplan konnte nicht geladen werden.
            </p>
            <Button variant="outline" onClick={() => refetch()}>
              Erneut versuchen
            </Button>
          </div>
        )}
        {!isLoading && data && (
          <KioskBoard board={data} lastUpdated={dataUpdatedAt} />
        )}
      </main>
    </div>
  );
}
