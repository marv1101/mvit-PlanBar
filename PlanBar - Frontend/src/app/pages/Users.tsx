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
import { Plus, Loader2, Trash2, Copy, Check, RotateCcw, AlertTriangle, Edit, Building2 } from 'lucide-react';
import { AppUser, Employee, Team } from '../types';
import { userFromResponse } from '../lib/mappers';
import * as userService from '../services/userService';
import * as teamService from '../services/teamService';
import { TIMEZONE } from '../lib/timezone';
import { toast } from 'sonner';
import { useApp } from '../context/AppContext';

export function Users() {
  const { employees: appEmployees } = useApp();
  const [users, setUsers] = useState<AppUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<AppUser | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState<AppUser | null>(null);
  const [allTeams, setAllTeams] = useState<Team[]>([]);

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await userService.getUsers();
      setUsers(data.items.map(userFromResponse));
    } catch {
      setError('Fehler beim Laden der Benutzer. Bitte versuchen Sie es erneut.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
    teamService.getTeams().then(res => setAllTeams(res.items)).catch(() => {});
  }, []);

  const handleDeleteClick = (user: AppUser) => {
    setUserToDelete(user);
    setDeleteDialogOpen(true);
  };

  const handleEditClick = (user: AppUser) => {
    setEditingUser(user);
    setEditDialogOpen(true);
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

  const getTeamById = (teamId: number) => {
    return allTeams.find(t => Number(t.id) === teamId);
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
            <UserCreateForm onSuccess={() => { setDialogOpen(false); loadUsers(); }} allEmployees={appEmployees} />
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
                      {user.role === 'admin' ? 'Administrator' : user.role === 'planer' ? 'Planer' : user.role === 'kiosk' ? 'Kiosk' : 'Mitarbeiter'}
                    </Badge>
                  </CardTitle>
                  <p className="text-sm text-gray-600 mt-1">{user.email}</p>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleEditClick(user)}
                    aria-label="Benutzer bearbeiten"
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeleteClick(user)}
                    aria-label="Benutzer löschen"
                  >
                    <Trash2 className="h-4 w-4 text-red-600" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
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

      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Benutzer bearbeiten</DialogTitle>
            <DialogDescription>
              Bearbeiten Sie die Benutzerdaten und Team-Zuordnung.
            </DialogDescription>
          </DialogHeader>
          {editingUser && (
            <UserEditForm
              user={editingUser}
              allTeams={allTeams}
              allEmployees={appEmployees}
              onSuccess={() => { setEditDialogOpen(false); loadUsers(); }}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface UserEditFormProps {
  user: AppUser;
  allTeams: Team[];
  allEmployees: Employee[];
  onSuccess: () => void;
}

function UserEditForm({ user, allTeams, allEmployees, onSuccess }: UserEditFormProps) {
  const [username, setUsername] = useState(user.username);
  const [email, setEmail] = useState(user.email);
  const [role, setRole] = useState(user.role === 'admin' ? 'admin' : user.role === 'planer' ? 'planer' : user.role === 'kiosk' ? 'kiosk' : 'user');
  const [employeeId, setEmployeeId] = useState<string>(user.employeeId ? String(user.employeeId) : 'none');
  const [teamIds, setTeamIds] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (employeeId && employeeId !== 'none') {
      const empId = Number(employeeId);
      import('../services/employeeService').then(svc =>
        svc.getEmployee(empId)
      ).then(emp => {
        setTeamIds(emp.team_ids ?? []);
      }).catch(() => {});
    } else {
      setTeamIds([]);
    }
  }, [employeeId]);

  const handleTeamToggle = (teamId: number) => {
    setTeamIds(prev =>
      prev.includes(teamId) ? prev.filter(id => id !== teamId) : [...prev, teamId]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await userService.updateUser(Number(user.id), {
        username,
        email,
        role,
        employee_id: employeeId !== 'none' ? Number(employeeId) : 0,
        team_ids: role === 'planer' && employeeId !== 'none' ? teamIds : null,
      });
      toast.success('Benutzer aktualisiert');
      onSuccess();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(Array.isArray(detail) ? detail.map((d: { msg: string }) => d.msg).join('; ') : detail || 'Ein Fehler ist aufgetreten');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="edit-username">Benutzername</Label>
        <Input
          id="edit-username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="edit-email">E-Mail</Label>
        <Input
          id="edit-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="edit-role">Rolle</Label>
        <Select value={role} onValueChange={setRole}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="user">Mitarbeiter</SelectItem>
            <SelectItem value="planer">Planer</SelectItem>
            <SelectItem value="kiosk">Kiosk</SelectItem>
            <SelectItem value="admin">Administrator</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="edit-employee">Mitarbeiter verknüpfen</Label>
        <Select value={employeeId} onValueChange={setEmployeeId}>
          <SelectTrigger>
            <SelectValue placeholder="Kein Mitarbeiter" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">Kein Mitarbeiter</SelectItem>
            {allEmployees.map((emp) => (
              <SelectItem key={emp.id} value={String(emp.id)}>
                {emp.name}{emp.email ? ` (${emp.email})` : ''}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {role === 'planer' && employeeId !== 'none' && (
        <div className="space-y-2">
          <Label className="mb-2 block flex items-center gap-1">
            <Building2 className="h-3.5 w-3.5" />
            Teams zuordnen
          </Label>
          <div className="space-y-2 max-h-[200px] overflow-y-auto">
            {allTeams.map((team) => (
              <label
                key={team.id}
                className="flex items-center gap-3 p-2 rounded-md hover:bg-gray-50 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={teamIds.includes(Number(team.id))}
                  onChange={() => handleTeamToggle(Number(team.id))}
                  className="rounded border-gray-300"
                />
                <span className="text-sm flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: team.color || '#9ca3af' }}
                  />
                  {team.name}
                </span>
              </label>
            ))}
            {allTeams.length === 0 && (
              <p className="text-xs text-gray-500">Keine Teams vorhanden.</p>
            )}
          </div>
        </div>
      )}

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
              Speichern...
            </>
          ) : (
            'Speichern'
          )}
        </Button>
      </div>
    </form>
  );
}

interface UserCreateFormProps {
  onSuccess: () => void;
  allEmployees: Employee[];
}

function UserCreateForm({ onSuccess, allEmployees }: UserCreateFormProps) {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('user');
  const [employeeId, setEmployeeId] = useState<string>('none');
  const [allTeams, setAllTeams] = useState<Team[]>([]);
  const [teamIds, setTeamIds] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<userService.AdminUserCreateResponseDTO | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    teamService.getTeams().then(res => setAllTeams(res.items)).catch(() => {});
  }, []);

  useEffect(() => {
    if (employeeId && employeeId !== 'none') {
      const empId = Number(employeeId);
      import('../services/employeeService').then(svc =>
        svc.getEmployee(empId)
      ).then(emp => {
        setTeamIds(emp.team_ids ?? []);
      }).catch(() => {});
    } else {
      setTeamIds([]);
    }
  }, [employeeId]);

  const handleTeamToggle = (teamId: number) => {
    setTeamIds(prev =>
      prev.includes(teamId) ? prev.filter(id => id !== teamId) : [...prev, teamId]
    );
  };

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
        team_ids: role === 'planer' && employeeId !== 'none' ? teamIds : undefined,
        // Kiosk-Zugänge sind reine Anzeige-Accounts (Tablett) und dürfen
        // nicht in den Passwort-Wechsel-Zwang bei der ersten Anmeldung laufen.
        must_change_password: role === 'kiosk' ? false : undefined,
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
            {result.must_change_password
              ? 'Der Benutzer muss bei der ersten Anmeldung ein neues Passwort vergeben.'
              : 'Der Benutzer kann sich direkt mit dem initialen Passwort anmelden (kein Passwortwechsel erzwungen).'}
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
            <SelectItem value="planer">Planer</SelectItem>
            <SelectItem value="kiosk">Kiosk</SelectItem>
            <SelectItem value="admin">Administrator</SelectItem>
          </SelectContent>
        </Select>
        {role === 'kiosk' && (
          <p className="text-xs text-gray-500">
            Kiosk-Benutzer sind reine Anzeige-Zugänge (z.&nbsp;B. Tablett an der Wand). Sie sehen den Dienstplan
            ohne Bearbeitungsrechte; das initiale Passwort bleibt gültig (kein Wechsel bei der ersten Anmeldung).
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="employee">Mitarbeiter verknüpfen (optional)</Label>
        <Select value={employeeId} onValueChange={setEmployeeId}>
          <SelectTrigger>
            <SelectValue placeholder="Kein Mitarbeiter" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">Kein Mitarbeiter</SelectItem>
            {allEmployees.map((emp) => (
              <SelectItem key={emp.id} value={String(emp.id)}>
                {emp.name}{emp.email ? ` (${emp.email})` : ''}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {allEmployees.length === 0 && (
          <p className="text-xs text-gray-500">Keine Mitarbeiter vorhanden. Bitte erstellen Sie zuerst Mitarbeiter.</p>
        )}
      </div>

      {role === 'planer' && employeeId !== 'none' && (
        <div className="space-y-2">
          <Label className="mb-2 block flex items-center gap-1">
            <Building2 className="h-3.5 w-3.5" />
            Teams zuordnen
          </Label>
          <div className="space-y-2 max-h-[200px] overflow-y-auto">
            {allTeams.map((team) => (
              <label
                key={team.id}
                className="flex items-center gap-3 p-2 rounded-md hover:bg-gray-50 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={teamIds.includes(Number(team.id))}
                  onChange={() => handleTeamToggle(Number(team.id))}
                  className="rounded border-gray-300"
                />
                <span className="text-sm flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: team.color || '#9ca3af' }}
                  />
                  {team.name}
                </span>
              </label>
            ))}
            {allTeams.length === 0 && (
              <p className="text-xs text-gray-500">Keine Teams vorhanden.</p>
            )}
          </div>
        </div>
      )}

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
