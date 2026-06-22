import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Loader2, Trash2, Copy, Check, RotateCcw, AlertTriangle } from 'lucide-react';
import { AppUser } from '../types';
import { userFromResponse } from '../lib/mappers';
import * as userService from '../services/userService';
import { TIMEZONE } from '../lib/timezone';

export function Users() {
  const [users, setUsers] = useState<AppUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState<AppUser | null>(null);

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await userService.getUsers();
      setUsers(data.map(userFromResponse));
    } catch {
      setError('Fehler beim Laden der Benutzer. Bitte versuchen Sie es erneut.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleDeleteClick = (user: AppUser) => {
    setUserToDelete(user);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!userToDelete) return;
    try {
      await userService.deleteUser(Number(userToDelete.id));
      setUsers(prev => prev.filter(u => u.id !== userToDelete.id));
    } catch {
      // error handled by api interceptor
    }
    setUserToDelete(null);
    setDeleteDialogOpen(false);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="font-semibold text-2xl mb-2">Benutzer</h2>
          <p className="text-gray-600">Verwalten Sie die Benutzerkonten für den Zugriff auf PlanBar</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-8 w-8 mx-auto text-blue-600 mb-4 animate-spin" />
            <p className="text-gray-600">Lade Benutzer...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="font-semibold text-2xl mb-2">Benutzer</h2>
          <p className="text-gray-600">Verwalten Sie die Benutzerkonten für den Zugriff auf PlanBar</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <AlertTriangle className="h-8 w-8 mx-auto text-red-500 mb-4" />
            <p className="text-red-600 font-medium mb-4">{error}</p>
            <Button onClick={loadUsers} variant="outline">
              <RotateCcw className="h-4 w-4 mr-2" />
              Erneut versuchen
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
        <div>
          <h2 className="font-semibold text-2xl mb-2">Benutzer</h2>
          <p className="text-gray-600">Verwalten Sie die Benutzerkonten für den Zugriff auf PlanBar</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Benutzer hinzufügen
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Neuen Benutzer anlegen</DialogTitle>
              <DialogDescription>
                Legen Sie einen neuen Benutzer an. Das initiale Passwort wird automatisch generiert.
              </DialogDescription>
            </DialogHeader>
            <UserCreateForm onSuccess={() => { setDialogOpen(false); loadUsers(); }} />
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {users.map((user) => (
          <Card key={user.id}>
            <CardHeader>
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    {user.username}
                    <Badge variant={user.role === 'admin' ? 'default' : 'secondary'}>
                      {user.role === 'admin' ? 'Administrator' : 'Mitarbeiter'}
                    </Badge>
                  </CardTitle>
                  <p className="text-sm text-gray-600 mt-1">{user.email}</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDeleteClick(user)}
                  aria-label="Benutzer löschen"
                >
                  <Trash2 className="h-4 w-4 text-red-600" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Letzte Anmeldung:</span>{' '}
                  {user.lastLogin
                    ? new Date(user.lastLogin).toLocaleDateString('de-DE', {
                        timeZone: TIMEZONE,
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })
                    : 'Noch nicht angemeldet'}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {users.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-gray-600 mb-4">Noch keine Benutzer vorhanden</p>
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Ersten Benutzer anlegen
            </Button>
          </CardContent>
        </Card>
      )}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Möchten Sie diesen Benutzer wirklich löschen?</AlertDialogTitle>
            <AlertDialogDescription>
              Diese Aktion kann nicht rückgängig gemacht werden.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Abbrechen</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-red-600 text-white hover:bg-red-700">
              Löschen
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

interface UserCreateFormProps {
  onSuccess: () => void;
}

function UserCreateForm({ onSuccess }: UserCreateFormProps) {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('user');
  const [employeeId, setEmployeeId] = useState<string>('none');
  const [unlinkedEmployees, setUnlinkedEmployees] = useState<userService.UnlinkedEmployeeDTO[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<userService.AdminUserCreateResponseDTO | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    userService.getUnlinkedEmployees().then(setUnlinkedEmployees).catch(() => {});
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const res = await userService.adminCreateUser({
        username,
        email,
        role,
        employee_id: employeeId !== 'none' ? Number(employeeId) : undefined,
      });
      setResult(res);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(Array.isArray(detail) ? detail.map((d: { msg: string }) => d.msg).join('; ') : detail || 'Ein Fehler ist aufgetreten');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = async () => {
    if (result) {
      await navigator.clipboard.writeText(result.initial_password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (result) {
    return (
      <div className="space-y-4">
        <Alert>
          <AlertDescription>
            Benutzer <strong>{result.username}</strong> wurde erfolgreich erstellt.
          </AlertDescription>
        </Alert>
        <div className="bg-gray-50 p-4 rounded-md space-y-2">
          <Label>Initiales Passwort</Label>
          <div className="flex items-center gap-2">
            <code className="flex-1 p-2 bg-white border rounded text-sm font-mono">
              {result.initial_password}
            </code>
            <Button variant="outline" size="sm" onClick={handleCopy} aria-label={copied ? 'Kopiert' : 'Passwort kopieren'}>
              {copied ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
            </Button>
          </div>
          <p className="text-xs text-gray-500">
            Der Benutzer muss bei der ersten Anmeldung ein neues Passwort vergeben.
          </p>
        </div>
        <div className="flex justify-end">
          <Button onClick={onSuccess}>Schließen</Button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="username">Benutzername</Label>
        <Input
          id="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="z.B. max.mustermann"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="email">E-Mail</Label>
        <Input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="max@apotheke.de"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="role">Rolle</Label>
        <Select value={role} onValueChange={setRole}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="user">Mitarbeiter</SelectItem>
            <SelectItem value="admin">Administrator</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="employee">Mitarbeiter verknüpfen (optional)</Label>
        <Select value={employeeId} onValueChange={setEmployeeId}>
          <SelectTrigger>
            <SelectValue placeholder="Kein Mitarbeiter" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">Kein Mitarbeiter</SelectItem>
            {unlinkedEmployees.map((emp) => (
              <SelectItem key={emp.id} value={String(emp.id)}>
                {emp.first_name} {emp.last_name}{emp.email ? ` (${emp.email})` : ''}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {unlinkedEmployees.length === 0 && (
          <p className="text-xs text-gray-500">Alle Mitarbeiter sind bereits verknüpft.</p>
        )}
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex justify-end gap-2">
        <Button type="submit" disabled={isLoading}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Erstelle...
            </>
          ) : (
            'Benutzer anlegen'
          )}
        </Button>
      </div>
    </form>
  );
}
