import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Plus, Edit, Trash2, Loader2 } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { EmployeeForm } from '../components/EmployeeForm';
import { Employee } from '../types';
import { Badge } from '../components/ui/badge';

export function Employees() {
  const { employees, deleteEmployee, roles, loading } = useApp();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);

  const handleEdit = (employee: Employee) => {
    setEditingEmployee(employee);
    setDialogOpen(true);
  };

  const handleDelete = (id: string) => {
    if (confirm('Möchten Sie diesen Mitarbeiter wirklich löschen?')) {
      deleteEmployee(id);
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingEmployee(null);
  };

  const getRoleById = (roleId: string) => {
    return roles.find(r => r.id === roleId);
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

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-semibold text-2xl mb-2">Mitarbeiter</h2>
          <p className="text-gray-600">Verwalten Sie Ihre Mitarbeiter und deren Arbeitszeiten</p>
        </div>
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
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleEdit(employee)}
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(employee.id)}
                  >
                    <Trash2 className="h-4 w-4 text-red-600" />
                  </Button>
                </div>
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
                  <div className="grid grid-cols-7 gap-1 text-xs">
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
    </div>
  );
}