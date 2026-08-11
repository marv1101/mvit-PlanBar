import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Repeat, Loader2, Send } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import {
  getMyShiftSwaps,
  createShiftSwap,
  getMySchedule,
} from '../services/selfService';
import { getEmployees } from '../services/employeeService';
import { useAuth } from '../context/AuthContext';
import { useApp } from '../context/AppContext';

const statusLabels: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' }> = {
  pending: { label: 'Ausstehend', variant: 'default' },
  approved: { label: 'Genehmigt', variant: 'outline' },
  rejected: { label: 'Abgelehnt', variant: 'destructive' },
};

const dayLabels = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

export function ShiftSwapForm() {
  const { user } = useAuth();
  const { schedules } = useApp();
  const queryClient = useQueryClient();
  const [targetEmployeeId, setTargetEmployeeId] = useState('');
  const [requesterShiftId, setRequesterShiftId] = useState('');
  const [targetShiftId, setTargetShiftId] = useState('');
  const [note, setNote] = useState('');

  const { data: myShifts } = useQuery({
    queryKey: ['my-schedule'],
    queryFn: getMySchedule,
  });

  const { data: allEmployees } = useQuery({
    queryKey: ['employees'],
    queryFn: () => getEmployees(),
  });

  const { data: mySwaps, isLoading: swapsLoading } = useQuery({
    queryKey: ['my-swaps'],
    queryFn: getMyShiftSwaps,
  });

  const createMutation = useMutation({
    mutationFn: createShiftSwap,
    onSuccess: () => {
      toast.success('Schichttausch angefragt');
      queryClient.invalidateQueries({ queryKey: ['my-swaps'] });
      setTargetEmployeeId('');
      setRequesterShiftId('');
      setTargetShiftId('');
      setNote('');
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : 'Fehler beim Erstellen';
      toast.error(msg);
    },
  });

  const otherEmployees = allEmployees?.items?.filter(e => String(e.id) !== user?.employeeId) || [];
  const targetShifts = useMemo(() => {
    if (!targetEmployeeId) return [];
    return schedules.flatMap(s => s.shifts)
      .filter(s => s.employeeId === targetEmployeeId)
      .map(s => ({
        id: Number(s.id),
        date: s.date,
        start_time: s.startTime,
        end_time: s.endTime,
      }));
  }, [schedules, targetEmployeeId]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!requesterShiftId || !targetEmployeeId || !targetShiftId) {
      toast.error('Bitte alle Felder ausfüllen');
      return;
    }
    createMutation.mutate({
      requester_shift_id: Number(requesterShiftId),
      target_employee_id: Number(targetEmployeeId),
      target_shift_id: Number(targetShiftId),
      note: note || undefined,
    });
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Repeat className="h-5 w-5" />
            Schichttausch anfragen
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="my-shift">Meine Schicht</Label>
              <select
                id="my-shift"
                className="w-full border rounded-md px-3 py-2 mt-1"
                value={requesterShiftId}
                onChange={e => setRequesterShiftId(e.target.value)}
              >
                <option value="">Bitte wählen...</option>
                {(myShifts || []).map(s => {
                  const d = new Date(s.date);
                  return (
                    <option key={s.id} value={s.id}>
                      {d.toLocaleDateString('de-DE')} {s.start_time.slice(0, 5)}-{s.end_time.slice(0, 5)}
                    </option>
                  );
                })}
              </select>
            </div>

            <div>
              <Label htmlFor="target-employee">Tauschpartner</Label>
              <select
                id="target-employee"
                className="w-full border rounded-md px-3 py-2 mt-1"
                value={targetEmployeeId}
                onChange={e => { setTargetEmployeeId(e.target.value); setTargetShiftId(''); }}
              >
                <option value="">Bitte wählen...</option>
                {otherEmployees.map(e => (
                  <option key={e.id} value={e.id}>{e.first_name} {e.last_name}</option>
                ))}
              </select>
            </div>

            <div>
              <Label htmlFor="target-shift">Wunsch-Schicht des Partners</Label>
              <select
                id="target-shift"
                className="w-full border rounded-md px-3 py-2 mt-1"
                value={targetShiftId}
                onChange={e => setTargetShiftId(e.target.value)}
                disabled={!targetEmployeeId}
              >
                <option value="">Bitte wählen...</option>
                {targetShifts.map(s => {
                  const d = new Date(s.date);
                  return (
                    <option key={s.id} value={s.id}>
                      {d.toLocaleDateString('de-DE')} {s.start_time.slice(0, 5)}-{s.end_time.slice(0, 5)}
                    </option>
                  );
                })}
              </select>
            </div>

            <div>
              <Label htmlFor="note">Notiz (optional)</Label>
              <Input
                id="note"
                value={note}
                onChange={e => setNote(e.target.value)}
                placeholder="Kurze Nachricht..."
              />
            </div>

            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Send className="h-4 w-4 mr-2" />
              )}
              Anfrage stellen
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Repeat className="h-5 w-5" />
            Meine Tauschanfragen
          </CardTitle>
        </CardHeader>
        <CardContent>
          {swapsLoading ? (
            <div className="text-center py-8">
              <Loader2 className="h-6 w-6 mx-auto animate-spin text-blue-600" />
            </div>
          ) : !mySwaps || mySwaps.length === 0 ? (
            <p className="text-gray-500 text-center py-8">Keine Tauschanfragen</p>
          ) : (
            <div className="space-y-3">
              {mySwaps.map(swap => (
                <div key={swap.id} className="border rounded-lg p-3">
                  <div className="flex items-center justify-between">
                    <div className="text-sm">
                      <p>
                        <span className="font-medium">Anfrage #{swap.id}</span>
                        {' - '}
                        {swap.status === 'pending' ? (
                          <span className="text-yellow-600">Ausstehend</span>
                        ) : swap.status === 'approved' ? (
                          <span className="text-green-600">Genehmigt</span>
                        ) : (
                          <span className="text-red-600">Abgelehnt</span>
                        )}
                      </p>
                      {swap.note && <p className="text-gray-500 text-xs mt-1">{swap.note}</p>}
                      {swap.rejection_reason && (
                        <p className="text-red-500 text-xs mt-1">Grund: {swap.rejection_reason}</p>
                      )}
                    </div>
                    <Badge variant={statusLabels[swap.status]?.variant || 'outline'}>
                      {statusLabels[swap.status]?.label || swap.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
