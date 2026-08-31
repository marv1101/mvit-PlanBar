import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Button } from '../components/ui/button';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Loader2, Lock, Mail } from 'lucide-react';

export function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const result = await login(email, password);
      if (!result.success) {
        setError('Ungültige E-Mail oder Passwort');
      }
    } catch (err) {
      setError('Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <div className="bg-blue-600 p-3 rounded-full">
              <Lock className="h-8 w-8 text-white" />
            </div>
          </div>
          <CardTitle className="text-2xl">MVIT PlanBar</CardTitle>
          <CardDescription>
            Ihr digitales Dienstplan- und Personalmanagement-Tool. Bitte melden Sie sich mit Ihren Zugangsdaten an.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">E-Mail</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <Input
                  id="email"
                  type="email"
                  placeholder="ihre.email@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10"
                  required
                  disabled={isLoading}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Passwort</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10"
                  required
                  disabled={isLoading}
                />
              </div>
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

          {import.meta.env.VITE_SHOW_DEMO_CREDENTIALS === 'true' &&
            (import.meta.env.VITE_DEMO_ADMIN_PASSWORD || import.meta.env.VITE_DEMO_USER_PASSWORD) && (
            <div className="mt-6 space-y-2 text-sm text-gray-600">
              <p className="text-center font-medium">Demo-Zugangsdaten:</p>
              {import.meta.env.VITE_DEMO_ADMIN_PASSWORD && (
                <div className="bg-gray-50 p-3 rounded-md space-y-1">
                  <p><strong>Administrator:</strong></p>
                  <p className="text-xs">E-Mail: admin@mphion.de</p>
                  <p className="text-xs">Passwort: {import.meta.env.VITE_DEMO_ADMIN_PASSWORD}</p>
                </div>
              )}
              {import.meta.env.VITE_DEMO_USER_PASSWORD && (
                <div className="bg-gray-50 p-3 rounded-md space-y-1">
                  <p><strong>Mitarbeiter:</strong></p>
                  <p className="text-xs">E-Mail: testuser@mphion.de</p>
                  <p className="text-xs">Passwort: {import.meta.env.VITE_DEMO_USER_PASSWORD}</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
