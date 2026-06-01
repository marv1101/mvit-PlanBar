import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Plus, Edit, Trash2, Loader2 } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { RequestForm } from '../components/RequestForm';
import { Request } from '../types';
import { Badge } from '../components/ui/badge';

const requestTypeLabels = {
  'urlaubswunsch': 'Urlaubswunsch',
  'bevorzugt': 'Bevorzugt',
  'nicht-verfügbar': 'Nicht verfügbar',
};

const requestTypeColors = {
  'urlaubswunsch': 'bg-blue-100 text-blue-800',
  'bevorzugt': 'bg-green-100 text-green-800',
  'nicht-verfügbar': 'bg-red-100 text-red-800',
};

export function Requests() {
  const { requests, deleteRequest, employees, loading } = useApp();
  const { user } = useAuth();
  const [editingRequest, setEditingRequest] = useState<Request | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), 1);
    const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    setStartDate(start.toISOString().split('T')[0]);
    setEndDate(end.toISOString().split('T')[0]);
  }, []);

  const isAdmin = user?.role === 'admin';
  const currentEmployeeId = user?.employeeId;

  const handleEdit = (request: Request) => {
    setEditingRequest(request);
    setIsDialogOpen(true);
  };

  const handleAdd = () => {
    setEditingRequest(null);
    setIsDialogOpen(true);
  };

  const handleDelete = (id: string) => {
    setDeletingId(id);
    setIsDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (deletingId) {
      deleteRequest(deletingId);
      setIsDeleteDialogOpen(false);
      setDeletingId(null);
    }
  };

  const handleClose = () => {
    setIsDialogOpen(false);
    setEditingRequest(null);
  };

  const getEmployeeName = (employeeId: string) => {
    const employee = employees.find(e => e.id === employeeId);
    return employee?.name || 'Unbekannt';
  };

  const getEmployeeColor = (employeeId: string) => {
    const employee = employees.find(e => e.id === employeeId);
    return employee?.color || '#gray';
  };

  // Filter requests based on user role
  const filteredRequests = isAdmin
    ? requests
    : requests.filter(req => req.employeeId === currentEmployeeId);

  const sortedRequests = [...filteredRequests].sort((a, b) =>
    new Date(a.date).getTime() - new Date(b.date).getTime()
  );

  const dateFilteredRequests = sortedRequests.filter(req => {
    if (!startDate || !endDate) return true;
    return req.date >= startDate && req.date <= endDate;
  });

  // Check if user can edit/delete a specific request
  const canModifyRequest = (request: Request) => {
    return isAdmin || request.employeeId === currentEmployeeId;
  };

  if (loading) {
    return (
      <div className="space-y-6">
      <div>
        <h2 className="font-semibold text-2xl mb-2">
          {isAdmin ? 'Mitarbeiterwünsche' : 'Meine Wünsche'}
        </h2>
        <p className="text-gray-600">Lade Wünsche...</p>
      </div>
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-8 w-8 mx-auto text-blue-600 mb-4 animate-spin" />
            <p className="text-gray-600">Lade Wünsche...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
        <div>
          <h2 className="font-semibold text-2xl mb-2">
            {isAdmin ? 'Mitarbeiterwünsche' : 'Meine Wünsche'}
          </h2>
          <p className="text-gray-600">
            {isAdmin
              ? 'Verwalten Sie Urlaubs- und Verfügbarkeitswünsche aller Mitarbeiter'
              : 'Tragen Sie Ihre Urlaubs- und Verfügbarkeitswünsche ein'}
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Wunsch hinzufügen
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {editingRequest ? 'Wunsch bearbeiten' : 'Neuer Wunsch'}
              </DialogTitle>
              <DialogDescription>
                {editingRequest ? 'Bearbeiten Sie den Mitarbeiterwunsch.' : 'Fügen Sie einen neuen Wunsch für einen Mitarbeiter hinzu.'}
              </DialogDescription>
            </DialogHeader>
            <RequestForm
              request={editingRequest}
              onClose={handleClose}
              currentEmployeeId={currentEmployeeId}
              isAdmin={isAdmin}
            />
          </DialogContent>
        </Dialog>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-end gap-4">
        <div>
          <Label htmlFor="filterStartDate">Von</Label>
          <Input
            id="filterStartDate"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="filterEndDate">Bis</Label>
          <Input
            id="filterEndDate"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {dateFilteredRequests.map((request) => (
          <Card key={request.id}>
            <CardHeader>
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-3 flex-1">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm"
                    style={{ backgroundColor: getEmployeeColor(request.employeeId) }}
                  >
                    {getEmployeeName(request.employeeId).split(' ').map(n => n[0]).join('')}
                  </div>
                  <div className="flex-1">
                    <CardTitle className="text-base">{getEmployeeName(request.employeeId)}</CardTitle>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-sm text-gray-600">
                        {new Date(request.date).toLocaleDateString('de-DE', {
                          weekday: 'long',
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </span>
                      <Badge variant="outline" className="text-xs">
                        Woche {request.week}
                      </Badge>
                    </div>
                  </div>
                </div>
                {canModifyRequest(request) && (
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEdit(request)}
                      aria-label="Wunsch bearbeiten"
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(request.id)}
                      aria-label="Wunsch löschen"
                    >
                      <Trash2 className="h-4 w-4 text-red-600" />
                    </Button>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Badge className={requestTypeColors[request.type]}>
                  {requestTypeLabels[request.type]}
                </Badge>
                {request.notes && (
                  <p className="text-sm text-gray-600 mt-2">{request.notes}</p>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {dateFilteredRequests.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-gray-600 mb-4">
              {isAdmin
                ? 'Noch keine Wünsche eingetragen'
                : 'Sie haben noch keine Wünsche eingetragen'}
            </p>
            <Button onClick={handleAdd}>
              <Plus className="h-4 w-4 mr-2" />
              {isAdmin ? 'Ersten Wunsch hinzufügen' : 'Wunsch hinzufügen'}
            </Button>
          </CardContent>
        </Card>
      )}

      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Wunsch löschen</AlertDialogTitle>
            <AlertDialogDescription>
              Möchten Sie diesen Wunsch wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.
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