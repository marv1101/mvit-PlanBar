import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Plus, Edit, Trash2, Loader2, RotateCcw, AlertTriangle, Building2 } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { EmployeeForm } from '../components/EmployeeForm';
import { Employee, Team } from '../types';
import { Badge } from '../components/ui/badge';
import * as teamService from '../services/teamService';

export function Employees() {
  const { user } = useAuth();
  const { employees, deleteEmployee, roles, loading, error, refresh } = useApp();
  const isAdmin = user?.role === 'admin';
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [employeeToDelete, setEmployeeToDelete] = useState<Employee | null>(null);
  const [allTeams, setAllTeams] = useState<Team[]>([]);

  React.useEffect(() => {
    teamService.getTeams().then(res => setAllTeams(res.items)).catch(() => {});
  }, []);

  const handleEdit = (employee: Employee) => {
    setEditingEmployee(employee);
    setDialogOpen(true);
  };

  const handleDeleteClick = (employee: Employee) => {
    setEmployeeToDelete(employee);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (employeeToDelete) {
      deleteEmployee(employeeToDelete.id);
      setEmployeeToDelete(null);
      setDeleteDialogOpen(false);
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingEmployee(null);
  };

  const getRoleById = (roleId: string) => {
    return roles.find(r => r.id === roleId);
  };

  const getTeamById = (teamId: number) => {
    return allTeams.find(t => Number(t.id) === teamId);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="font-semibold text-2xl mb-2">Mitarbeiter</h2>
          <p className="text-gray-600">Verwalten Sie Ihre Mitarbeiter und deren Arbeitszeiten</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-8 w-8 mx-auto text-blue-600 mb-4 animate-spin" />
            <p className="text-gray-600">Lade Mitarbeiter...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="font-semibold text-2xl mb-2">Mitarbeiter</h2>
          <p className="text-gray-600">Verwalten Sie Ihre Mitarbeiter und deren Arbeitszeiten</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <AlertTriangle className="h-8 w-8 mx-auto text-red-500 mb-4" />
            <p className="text-red-600 font-medium mb-4">{error}</p>
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
          <h2 className="font-semibold text-2xl mb-2">Mitarbeiter</h2>
          <p className="text-gray-600">Verwalten Sie Ihre Mitarbeiter und deren Arbeitszeiten</p>
        </div>
        {isAdmin && (
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Mitarbeiter hinzufügen
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingEmployee ? 'Mitarbeiter bearbeiten' : 'Neuer Mitarbeiter'}
              </DialogTitle>
              <DialogDescription>
                {editingEmployee ? 'Bearbeiten Sie die Mitarbeiterdaten und Arbeitszeiten.' : 'Fügen Sie einen neuen Mitarbeiter mit individuellen Arbeitszeiten hinzu.'}
              </DialogDescription>
            </DialogHeader>
            <EmployeeForm employee={editingEmployee} onClose={handleCloseDialog} />
          </DialogContent>
        </Dialog>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4">
        {employees.map((employee) => (
          <Card key={employee.id}>
            <CardHeader>
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-white"
                    style={{ backgroundColor: employee.color }}
                  >
                    {employee.name.split(' ').map(n => n[0]).join('')}
                  </div>
                  <div>
                    <CardTitle>{employee.name}</CardTitle>
                    <p className="text-sm text-gray-600">{employee.email}</p>
                  </div>
                </div>
                {isAdmin && (
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleEdit(employee)}
                    aria-label="Mitarbeiter bearbeiten"
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeleteClick(employee)}
                    aria-label="Mitarbeiter löschen"
                  >
                    <Trash2 className="h-4 w-4 text-red-600" />
                  </Button>
                </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium mb-2">Rollen</p>
                  <div className="flex flex-wrap gap-2">
                    {employee.roles.map(roleId => {
                      const role = getRoleById(roleId);
                      return role ? (
                        <Badge key={roleId} variant="secondary" style={{ backgroundColor: role.color + '20', color: role.color }}>
                          {role.name}
                        </Badge>
                      ) : null;
                    })}
                    {employee.roles.length === 0 && (
                      <span className="text-sm text-gray-500">Keine Rollen zugewiesen</span>
                    )}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium mb-2 flex items-center gap-1">
                    <Building2 className="h-3.5 w-3.5" />
                    Teams
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {(employee.teamIds ?? []).map(teamId => {
                      const team = getTeamById(teamId);
                      return team ? (
                        <Badge key={teamId} variant="secondary" style={{ backgroundColor: (team.color || '#9ca3af') + '20', color: team.color || '#6b7280' }}>
                          {team.name}
                        </Badge>
                      ) : null;
                    })}
                    {(employee.teamIds ?? []).length === 0 && (
                      <span className="text-sm text-gray-500">Kein Team zugewiesen</span>
                    )}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium mb-2">Pausenzeit</p>
                  <p className="text-sm text-gray-600">
                    {employee.breakTime.start} - {employee.breakTime.end} ({employee.breakTime.duration} Min.)
                  </p>
                </div>
                {employee.maxWorkHours && (
                  <div>
                    <p className="text-sm font-medium mb-2">Maximale Arbeitszeit</p>
                    <p className="text-sm text-gray-600">
                      {employee.maxWorkHours} Stunden pro Woche
                    </p>
                  </div>
                )}
                <div>
                  <p className="text-sm font-medium mb-2">Arbeitszeiten Woche A</p>
                  <div className="grid grid-cols-3 sm:grid-cols-7 gap-1 text-xs">
                    {Object.entries(employee.workingHours.weekA).map(([day, hours]) => (
                      <div
                        key={day}
                        className={`p-2 rounded text-center ${
                          hours.enabled ? 'bg-green-50 text-green-900' : 'bg-gray-100 text-gray-500'
                        }`}
                      >
                        <div className="font-medium capitalize">{day.slice(0, 2)}</div>
                        {hours.enabled && (
                          <div className="mt-1">
                            {hours.start.slice(0, 5)}<br />-<br />{hours.end.slice(0, 5)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {employees.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-gray-600 mb-4">Noch keine Mitarbeiter hinzugefügt</p>
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Ersten Mitarbeiter hinzufügen
            </Button>
          </CardContent>
        </Card>
      )}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Möchten Sie diesen Mitarbeiter wirklich löschen?</AlertDialogTitle>
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