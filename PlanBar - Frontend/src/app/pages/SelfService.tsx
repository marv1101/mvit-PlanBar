import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { Plus, Loader2, Calendar, Clock, Repeat, CalendarDays } from 'lucide-react';
import { toast } from 'sonner';
import { MyScheduleView } from '../components/MyScheduleView';
import { ShiftSwapForm } from '../components/ShiftSwapForm';
import { AvailabilityEditor } from '../components/AvailabilityEditor';
import { RequestForm } from '../components/RequestForm';
import { TIMEZONE } from '../lib/timezone';
import type { Request } from '../types';

const requestTypeColors: Record<string, string> = {
  'urlaubswunsch': 'bg-blue-100 text-blue-800',
  'bevorzugt': 'bg-green-100 text-green-800',
  'nicht-verfügbar': 'bg-red-100 text-red-800',
  'vacation': 'bg-blue-100 text-blue-800',
};

const statusLabels: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  approved: { label: 'Freigegeben', variant: 'outline' },
  pending: { label: 'Ausstehend', variant: 'default' },
  rejected: { label: 'Abgelehnt', variant: 'destructive' },
};

export function SelfService() {
  const { requests, deleteRequest, employees, loading } = useApp();
  const { user } = useAuth();
  const [editingRequest, setEditingRequest] = useState<Request | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const currentEmployeeId = user?.employeeId;

  const myVacationRequests = (requests || []).filter(
    r => r.employeeId === currentEmployeeId && (r.type === 'urlaubswunsch' || r.type === 'vacation')
  ).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  const handleAddVacation = () => {
    setEditingRequest(null);
    setIsDialogOpen(true);
  };

  const handleClose = () => {
    setIsDialogOpen(false);
    setEditingRequest(null);
  };

  const tabs = [
    { value: 'schedule', label: 'Mein Dienstplan', icon: Calendar },
    { value: 'shift-swap', label: 'Schichttausch', icon: Repeat },
    { value: 'vacation', label: 'Urlaub', icon: Clock },
    { value: 'availability', label: 'Verfügbarkeit', icon: CalendarDays },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-semibold text-2xl mb-2">Self-Service</h2>
        <p className="text-gray-600">Verwalten Sie Ihre eigenen Daten selbstständig</p>
      </div>

      <Tabs defaultValue="schedule">
        <TabsList className="w-full flex-wrap">
          {tabs.map(t => {
            const Icon = t.icon;
            return (
              <TabsTrigger key={t.value} value={t.value} className="flex-1 min-w-[120px]">
                <Icon className="h-4 w-4 mr-2" />
                {t.label}
              </TabsTrigger>
            );
          })}
        </TabsList>

        <TabsContent value="schedule" className="mt-6">
          <MyScheduleView />
        </TabsContent>

        <TabsContent value="shift-swap" className="mt-6">
          <ShiftSwapForm />
        </TabsContent>

        <TabsContent value="vacation" className="mt-6">
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-lg font-semibold">Meine Urlaubsanträge</h3>
                <p className="text-sm text-gray-600">Übersicht und Status Ihrer Urlaubsanträge</p>
              </div>
              <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                <DialogTrigger asChild>
                  <Button onClick={handleAddVacation}>
                    <Plus className="h-4 w-4 mr-2" />
                    Urlaub beantragen
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Urlaub beantragen</DialogTitle>
                    <DialogDescription>
                      Tragen Sie Ihren Urlaubswunsch ein. Der Status wird nach Prüfung aktualisiert.
                    </DialogDescription>
                  </DialogHeader>
                  <RequestForm
                    request={editingRequest}
                    onClose={handleClose}
                    currentEmployeeId={currentEmployeeId}
                    isAdmin={false}
                    defaultType="urlaubswunsch"
                  />
                </DialogContent>
              </Dialog>
            </div>

            {loading ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Loader2 className="h-8 w-8 mx-auto text-blue-600 mb-4 animate-spin" />
                  <p className="text-gray-600">Lade Urlaubsanträge...</p>
                </CardContent>
              </Card>
            ) : myVacationRequests.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <p className="text-gray-600 mb-4">Keine Urlaubsanträge vorhanden</p>
                  <Button onClick={handleAddVacation}>
                    <Plus className="h-4 w-4 mr-2" />
                    Urlaub beantragen
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {myVacationRequests.map(req => (
                  <Card key={req.id}>
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">
                            {new Date(req.date).toLocaleDateString('de-DE', { timeZone: TIMEZONE, weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                          </p>
                          {req.notes && <p className="text-sm text-gray-600 mt-1">{req.notes}</p>}
                          {req.rejectionReason && (
                            <p className="text-xs text-red-600 mt-1">Grund: {req.rejectionReason}</p>
                          )}
                        </div>
                        <Badge variant={statusLabels[req.status || 'pending']?.variant || 'outline'}>
                          {statusLabels[req.status || 'pending']?.label || req.status}
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="availability" className="mt-6">
          <AvailabilityEditor />
        </TabsContent>
      </Tabs>
    </div>
  );
}
