import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Plus, Edit, Trash2, Loader2 } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Role } from '../types';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';

const colors = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#14b8a6', // teal
  '#f97316', // orange
];

export function Roles() {
  const { roles, addRole, updateRole, deleteRole, loading } = useApp();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);

  const handleEdit = (role: Role) => {
    setEditingRole(role);
    setDialogOpen(true);
  };

  const handleDelete = (id: string) => {
    if (confirm('Möchten Sie diese Rolle wirklich löschen?')) {
      deleteRole(id);
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingRole(null);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-8 w-8 mx-auto text-blue-600 mb-4 animate-spin" />
            <p className="text-gray-600">Lade Rollen...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
        <div>
          <h1 className="text-3xl font-bold">Rollenverwaltung</h1>
          <p className="text-gray-600 mt-1">Verwalten Sie die verfügbaren Rollen/Fähigkeiten</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => setEditingRole(null)}>
              <Plus className="mr-2 h-4 w-4" />
              Neue Rolle
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingRole ? 'Rolle bearbeiten' : 'Neue Rolle erstellen'}</DialogTitle>
              <DialogDescription>
                {editingRole ? 'Bearbeiten Sie die Rolleninformationen' : 'Erstellen Sie eine neue Rolle für Ihre Mitarbeiter'}
              </DialogDescription>
            </DialogHeader>
            <RoleForm role={editingRole} onClose={handleCloseDialog} />
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {roles.map((role) => (
          <Card key={role.id}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <div
                  className="w-4 h-4 rounded-full"
                  style={{ backgroundColor: role.color }}
                />
                {role.name}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleEdit(role)}
                  aria-label="Rolle bearbeiten"
                >
                  <Edit className="h-4 w-4" />
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => handleDelete(role.id)}
                  aria-label="Rolle löschen"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}

        {roles.length === 0 && (
          <div className="col-span-full text-center py-12">
            <p className="text-gray-500 mb-4">Keine Rollen vorhanden</p>
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Erste Rolle erstellen
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

interface RoleFormProps {
  role: Role | null;
  onClose: () => void;
}

function RoleForm({ role, onClose }: RoleFormProps) {
  const { addRole, updateRole } = useApp();
  const [formData, setFormData] = useState<Role>(
    role || {
      id: Date.now().toString(),
      name: '',
      color: colors[0],
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (role) {
      updateRole(role.id, formData);
    } else {
      addRole(formData);
    }
    onClose();
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="name">Rollenname</Label>
        <Input
          id="name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="z.B. Apotheker, PTA, PKA..."
          required
        />
      </div>

      <div>
        <Label>Farbe</Label>
        <div className="flex gap-2 mt-2">
          {colors.map((color) => (
            <button
              key={color}
              type="button"
              className={`w-8 h-8 rounded-full border-2 ${
                formData.color === color ? 'border-gray-900' : 'border-gray-300'
              }`}
              style={{ backgroundColor: color }}
              onClick={() => setFormData({ ...formData, color })}
            />
          ))}
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onClose}>
          Abbrechen
        </Button>
        <Button type="submit">
          {role ? 'Speichern' : 'Erstellen'}
        </Button>
      </div>
    </form>
  );
}
