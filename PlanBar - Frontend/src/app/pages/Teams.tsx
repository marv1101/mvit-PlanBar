import React, { useEffect, useMemo, useState } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Alert, AlertDescription } from '../components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/alert-dialog';
import { Checkbox } from '../components/ui/checkbox';
import { Plus, Edit, Trash2, Loader2, RotateCcw, AlertTriangle, Building2 } from 'lucide-react';
import { Team } from '../types';
import * as teamService from '../services/teamService';
import { toast } from 'sonner';

const colors = [
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#ec4899',
  '#14b8a6',
  '#f97316',
];

export function Teams() {
  const { employees, loading: appLoading, error: appError, refresh: refreshApp } = useApp();
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTeam, setEditingTeam] = useState<Team | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [teamToDelete, setTeamToDelete] = useState<Team | null>(null);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [teamToAssign, setTeamToAssign] = useState<Team | null>(null);
  const [assignedEmployeeIds, setAssignedEmployeeIds] = useState<number[]>([]);

  const loadTeams = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await teamService.getTeams();
      setTeams(res.items);
    } catch {
      setError('Fehler beim Laden der Teams.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTeams();
  }, []);

  const handleEdit = (team: Team) => {
    setEditingTeam(team);
    setDialogOpen(true);
  };

  const handleAssignClick = async (team: Team) => {
    setTeamToAssign(team);
    setAssignedEmployeeIds([]);
    try {
      const data = await teamService.getTeam(Number(team.id));
      setAssignedEmployeeIds((data as unknown as { employee_ids: number[] }).employee_ids ?? []);
    } catch {
      toast.error('Fehler beim Laden der Team-Mitglieder');
    }
    setAssignDialogOpen(true);
  };

  const handleDeleteClick = (team: Team) => {
    setTeamToDelete(team);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!teamToDelete) return;
    try {
      await teamService.deleteTeam(Number(teamToDelete.id));
      setTeams((prev) => prev.filter((t) => t.id !== teamToDelete.id));
      toast.success('Team gelöscht');
    } catch {
      toast.error('Fehler beim Löschen des Teams');
    }
    setTeamToDelete(null);
    setDeleteDialogOpen(false);
  };

  const handleSaveAssignments = async () => {
    if (!teamToAssign) return;
    try {
      await teamService.assignTeamEmployees(Number(teamToAssign.id), {
        employee_ids: assignedEmployeeIds,
      });
      toast.success('Team-Mitglieder aktualisiert');
      setAssignDialogOpen(false);
    } catch {
      toast.error('Fehler beim Aktualisieren der Team-Mitglieder');
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingTeam(null);
  };

  const refresh = async () => {
    await loadTeams();
    await refreshApp();
  };

  if (loading || appLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Teams</h1>
          <p className="text-gray-600 mt-1">Verwalten Sie die Teams für die Schichtplanung</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-8 w-8 mx-auto text-blue-600 mb-4 animate-spin" />
            <p className="text-gray-600">Lade Teams...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || appError) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Teams</h1>
          <p className="text-gray-600 mt-1">Verwalten Sie die Teams für die Schichtplanung</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <AlertTriangle className="h-8 w-8 mx-auto text-red-500 mb-4" />
            <p className="text-red-600 font-medium mb-4">{error || appError}</p>
            <Button onClick={refresh} variant="outline">
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
          <h1 className="text-3xl font-bold">Teams</h1>
          <p className="text-gray-600 mt-1">Verwalten Sie die Teams für die Schichtplanung</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => setEditingTeam(null)}>
              <Plus className="mr-2 h-4 w-4" />
              Neues Team
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingTeam ? 'Team bearbeiten' : 'Neues Team erstellen'}</DialogTitle>
              <DialogDescription>
                {editingTeam ? 'Bearbeiten Sie die Teaminformationen' : 'Erstellen Sie ein neues Team für die Schichtplanung'}
              </DialogDescription>
            </DialogHeader>
            <TeamForm team={editingTeam} onClose={handleCloseDialog} onSaved={loadTeams} />
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {teams.map((team) => (
          <Card key={team.id}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <div
                  className="w-4 h-4 rounded-full"
                  style={{ backgroundColor: team.color || '#9ca3af' }}
                />
                {team.name}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600 mb-4">{team.description || 'Keine Beschreibung'}</p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => handleEdit(team)}>
                  <Edit className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleAssignClick(team)}>
                  <Building2 className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleDeleteClick(team)}>
                  <Trash2 className="h-4 w-4 text-red-600" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {teams.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-gray-600 mb-4">Noch keine Teams vorhanden</p>
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Erstes Team anlegen
            </Button>
          </CardContent>
        </Card>
      )}

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Team löschen?</AlertDialogTitle>
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

      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Mitarbeiter zuweisen</DialogTitle>
            <DialogDescription>
              Wählen Sie die Mitarbeiter aus, die dem Team <strong>{teamToAssign?.name}</strong> angehören sollen.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[300px] overflow-y-auto space-y-2 py-2">
            {employees.map((emp) => (
              <label
                key={emp.id}
                className="flex items-center gap-3 p-2 rounded-md hover:bg-gray-50 cursor-pointer"
              >
                <Checkbox
                  checked={assignedEmployeeIds.includes(Number(emp.id))}
                  onCheckedChange={(checked) => {
                    const id = Number(emp.id);
                    setAssignedEmployeeIds((prev) =>
                      checked ? [...prev, id] : prev.filter((x) => x !== id)
                    );
                  }}
                />
                <span className="text-sm">
                  {emp.name}
                </span>
              </label>
            ))}
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setAssignDialogOpen(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleSaveAssignments}>Speichern</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface TeamFormProps {
  team: Team | null;
  onClose: () => void;
  onSaved: () => void;
}

function TeamForm({ team, onClose, onSaved }: TeamFormProps) {
  const [name, setName] = useState(team?.name ?? '');
  const [description, setDescription] = useState(team?.description ?? '');
  const [color, setColor] = useState(team?.color ?? colors[0]);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    if (!name.trim()) {
      setFormError('Name ist erforderlich');
      return;
    }
    setSaving(true);
    try {
      if (team) {
        await teamService.updateTeam(Number(team.id), { name, description, color });
      } else {
        await teamService.createTeam({ name, description, color });
      }
      toast.success(team ? 'Team aktualisiert' : 'Team erstellt');
      onSaved();
      onClose();
    } catch {
      setFormError('Fehler beim Speichern des Teams');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Name</Label>
        <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required />
      </div>
      <div className="space-y-2">
        <Label htmlFor="description">Beschreibung</Label>
        <Input id="description" value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>
      <div className="space-y-2">
        <Label>Farbe</Label>
        <div className="flex flex-wrap gap-2">
          {colors.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setColor(c)}
              className={`w-8 h-8 rounded-full border-2 ${color === c ? 'border-gray-900' : 'border-transparent'}`}
              style={{ backgroundColor: c }}
              aria-label={`Farbe ${c}`}
            />
          ))}
        </div>
      </div>
      {formError && (
        <Alert variant="destructive">
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onClose}>
          Abbrechen
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Speichern'}
        </Button>
      </div>
    </form>
  );
}
