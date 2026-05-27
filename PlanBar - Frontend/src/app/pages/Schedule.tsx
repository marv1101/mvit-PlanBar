import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Calendar, Sparkles, Download, Eye, Trash2, CalendarDays, Loader2, Send, RotateCcw, Pen, X } from 'lucide-react';
import { Schedule as ScheduleType, WeekType } from '../types';
import { ScheduleCalendar } from '../components/ScheduleCalendar';
import { EditableScheduleCalendar } from '../components/EditableScheduleCalendar';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import * as scheduleService from '../services/scheduleService';
import { scheduleFromResponse, shiftplanToShift } from '../lib/mappers';

const STATUS_LABELS: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  draft: { label: 'Entwurf', variant: 'secondary' },
  submitted: { label: 'Wird berechnet...', variant: 'default' },
  completed: { label: 'Abgeschlossen', variant: 'outline' },
  failed: { label: 'Fehlgeschlagen', variant: 'destructive' },
};

function StatusBadge({ status }: { status: string }) {
  const config = STATUS_LABELS[status] || { label: status, variant: 'secondary' as const };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}

export function Schedule() {
  const {
    employees,
    requests,
    schedules,
    addSchedule,
    updateSchedule,
    deleteSchedule,
    currentWeek,
    setCurrentWeek,
    roles,
    loading,
    refresh,
  } = useApp();

  const [activeTab, setActiveTab] = useState<'create' | 'manage'>('create');
  const [selectedSchedule, setSelectedSchedule] = useState<ScheduleType | null>(null);

  const [scheduleName, setScheduleName] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [roleRequirements, setRoleRequirements] = useState<Record<string, number>>({});
  const [submitting, setSubmitting] = useState(false);
  const [currentScheduleId, setCurrentScheduleId] = useState<string | null>(null);
  const [currentScheduleStatus, setCurrentScheduleStatus] = useState<string | null>(null);
  const [pollResult, setPollResult] = useState<ScheduleType | null>(null);

  const [creationMode, setCreationMode] = useState<'tito' | 'manual'>('tito');
  const [manualName, setManualName] = useState('');
  const [manualStartDate, setManualStartDate] = useState('');
  const [manualEndDate, setManualEndDate] = useState('');
  const [manualWeekType, setManualWeekType] = useState<WeekType>('A');
  const [manuallyCreatedSchedule, setManuallyCreatedSchedule] = useState<ScheduleType | null>(null);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    return stopPolling;
  }, [stopPolling]);

  useEffect(() => {
    if (currentScheduleId && currentScheduleStatus === 'submitted') {
      pollRef.current = setInterval(async () => {
        try {
          const res = await scheduleService.getSchedule(Number(currentScheduleId));
          setCurrentScheduleStatus(res.status);
          if (res.status === 'completed') {
            stopPolling();
            setSubmitting(false);
            setPollResult(scheduleFromResponse(res));
            toast.success('Schichtplan wurde von TiTO berechnet');
            refresh();
          } else if (res.status === 'failed') {
            stopPolling();
            setSubmitting(false);
            setPollResult(scheduleFromResponse(res));
            const diagnostics = res.diagnostics_json as { info?: string } | null;
            const msg = diagnostics?.info || 'TiTO-Berechnung fehlgeschlagen';
            toast.error(msg, { duration: 8000 });
            refresh();
          }
        } catch {
          stopPolling();
          setSubmitting(false);
          toast.error('Fehler beim Abrufen des Status');
        }
      }, 3000);
    }
  }, [currentScheduleId, currentScheduleStatus, stopPolling, refresh]);

  const handleRoleRequirementChange = (roleId: string, value: number) => {
    setRoleRequirements(prev => ({ ...prev, [roleId]: value }));
  };

  const createAndSubmit = async () => {
    if (!scheduleName || !startDate || !endDate) {
      toast.error('Bitte Name, Start- und Enddatum eingeben');
      return;
    }

    setSubmitting(true);
    setPollResult(null);
    setCurrentScheduleId(null);
    setCurrentScheduleStatus(null);

    try {
      const created = await scheduleService.createSchedule({
        name: scheduleName,
        start_date: startDate,
        end_date: endDate,
        role_requirements: Object.keys(roleRequirements).length > 0 ? roleRequirements : undefined,
        shiftplans: [],
      });

      const mapped = scheduleFromResponse(created);
      addSchedule(mapped);

      setCurrentScheduleId(mapped.id);
      setCurrentScheduleStatus('submitted');

      const submitted = await scheduleService.submitScheduleToTito(created.id);
      setCurrentScheduleStatus(submitted.status);

      toast.success('Schichtplan an TiTO übermittelt');
    } catch {
      setSubmitting(false);
      setCurrentScheduleId(null);
      setCurrentScheduleStatus(null);
      toast.error('Fehler beim Erstellen oder Übermitteln des Schichtplans');
    }
  };

  const createManual = async () => {
    if (!manualName || !manualStartDate || !manualEndDate) {
      toast.error('Bitte Name, Start- und Enddatum eingeben');
      return;
    }

    try {
      const created = await scheduleService.createSchedule({
        name: manualName,
        start_date: manualStartDate,
        end_date: manualEndDate,
        week_type: manualWeekType,
        shiftplans: [],
      });

      const mapped = scheduleFromResponse(created);
      addSchedule(mapped);
      setManuallyCreatedSchedule(mapped);
      toast.success('Schichtplan erstellt');
    } catch {
      toast.error('Fehler beim Erstellen des Schichtplans');
    }
  };

  const handleManualSave = async (shifts: ScheduleType['shifts']): Promise<void> => {
    if (!manuallyCreatedSchedule) return;

    const shiftplans = shifts.map(s => ({
      employee_id: Number(s.employeeId),
      date: s.date,
      shift_id: s.id,
      start_time: s.startTime,
      end_time: s.endTime,
      week: s.week,
      break_start: s.breakStart,
      break_end: s.breakEnd,
    }));

    await scheduleService.replaceAllShifts(Number(manuallyCreatedSchedule.id), shiftplans);
    await refresh();
    setManuallyCreatedSchedule(null);
    setManualName('');
    setManualStartDate('');
    setManualEndDate('');
    setManualWeekType('A');
    setCreationMode('tito');
    toast.success('Schichtplan gespeichert');
  };

  const handleViewSchedule = async (schedule: ScheduleType) => {
    try {
      const res = await scheduleService.getSchedule(Number(schedule.id));
      setSelectedSchedule(scheduleFromResponse(res));
    } catch {
      setSelectedSchedule(schedule);
    }
  };

  const handleSubmitExisting = async (schedule: ScheduleType) => {
    try {
      await scheduleService.submitScheduleToTito(Number(schedule.id));
      toast.success('Schichtplan an TiTO übermittelt');
      refresh();
      setCurrentScheduleId(schedule.id);
      setCurrentScheduleStatus('submitted');
    } catch {
      toast.error('Fehler beim Übermitteln an TiTO');
    }
  };

  const handleRetry = async (schedule: ScheduleType) => {
    try {
      await scheduleService.retrySchedule(Number(schedule.id));
      toast.success('Schichtplan wird erneut an TiTO gesendet');
      refresh();
      setCurrentScheduleId(schedule.id);
      setCurrentScheduleStatus('submitted');
    } catch {
      toast.error('Fehler beim erneuten Senden');
    }
  };

  const handleDeleteSchedule = (schedule: ScheduleType) => {
    if (confirm(`Möchten Sie den Schichtplan "${schedule.name}" wirklich löschen?`)) {
      deleteSchedule(schedule.id);
      if (selectedSchedule?.id === schedule.id) {
        setSelectedSchedule(null);
      }
    }
  };

  const handleManageSave = async (shifts: ScheduleType['shifts']): Promise<void> => {
    if (!selectedSchedule) return;

    const shiftplans = shifts.map(s => ({
      employee_id: Number(s.employeeId),
      date: s.date,
      shift_id: s.id,
      start_time: s.startTime,
      end_time: s.endTime,
      week: s.week,
      break_start: s.breakStart,
      break_end: s.breakEnd,
    }));

    await scheduleService.replaceAllShifts(Number(selectedSchedule.id), shiftplans);
    await refresh();
    setSelectedSchedule(prev => prev ? { ...prev, shifts } : null);
    toast.success('Schichtplan gespeichert');
  };

  const handleUpdateSchedule = (updatedSchedule: ScheduleType) => {
    updateSchedule(updatedSchedule.id, updatedSchedule);
    setSelectedSchedule(updatedSchedule);
  };

  const exportShifts = (shifts: ScheduleType['shifts'], name: string) => {
    if (shifts.length === 0) {
      toast.error('Keine Schichten zum Exportieren');
      return;
    }

    const headers = ['Datum', 'Woche', 'Mitarbeiter', 'Start', 'Ende', 'Pause Start', 'Pause Ende'];
    const rows = shifts.map(shift => {
      const employee = employees.find(e => e.id === shift.employeeId);
      return [
        new Date(shift.date).toLocaleDateString('de-DE'),
        shift.week,
        employee?.name || '',
        shift.startTime,
        shift.endTime,
        shift.breakStart || '',
        shift.breakEnd || '',
      ];
    });

    const csvContent = [headers, ...rows].map(row => row.join(';')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `schichtplan-${name}.csv`;
    link.click();
    toast.success('Schichtplan exportiert');
  };

  const displayShifts = pollResult?.shifts || [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-semibold text-2xl mb-2">Schichtplanung</h2>
        <p className="text-gray-600">Erstellen und verwalten Sie Ihre Schichtpläne</p>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'create' | 'manage')}>
        <TabsList>
          <TabsTrigger value="create">
            <Sparkles className="h-4 w-4 mr-2" />
            Neu erstellen
          </TabsTrigger>
          <TabsTrigger value="manage">
            <CalendarDays className="h-4 w-4 mr-2" />
            Verwalten ({schedules.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="create" className="space-y-6">
          {!currentScheduleId && !manuallyCreatedSchedule && (
            <>
              <Card>
                <CardContent className="pt-6">
                  <div className="flex gap-2">
                    <Button
                      variant={creationMode === 'tito' ? 'default' : 'outline'}
                      onClick={() => setCreationMode('tito')}
                    >
                      <Send className="h-4 w-4 mr-2" />
                      Über TiTO
                    </Button>
                    <Button
                      variant={creationMode === 'manual' ? 'default' : 'outline'}
                      onClick={() => setCreationMode('manual')}
                    >
                      <Pen className="h-4 w-4 mr-2" />
                      Manuell
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {creationMode === 'tito' && (
                <Card>
                  <CardHeader>
                    <CardTitle>Schichtplan-Einstellungen</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <Label htmlFor="scheduleName">Plan-Name</Label>
                      <Input
                        id="scheduleName"
                        value={scheduleName}
                        onChange={(e) => setScheduleName(e.target.value)}
                        placeholder="z.B. April 2026"
                        disabled={submitting}
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="startDate">Startdatum</Label>
                        <Input
                          id="startDate"
                          type="date"
                          value={startDate}
                          onChange={(e) => setStartDate(e.target.value)}
                          disabled={submitting}
                        />
                      </div>
                      <div>
                        <Label htmlFor="endDate">Enddatum</Label>
                        <Input
                          id="endDate"
                          type="date"
                          value={endDate}
                          onChange={(e) => setEndDate(e.target.value)}
                          disabled={submitting}
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Rollenanforderungen pro Tag</Label>
                      <div className="grid grid-cols-2 gap-4">
                        {roles.map(role => (
                          <div key={role.id}>
                            <Label htmlFor={`role-${role.id}`} className="flex items-center gap-2">
                              <div
                                className="w-3 h-3 rounded-full"
                                style={{ backgroundColor: role.color }}
                              />
                              {role.name}
                            </Label>
                            <Input
                              id={`role-${role.id}`}
                              type="number"
                              min="0"
                              value={roleRequirements[role.id] || 0}
                              onChange={(e) => handleRoleRequirementChange(role.id, parseInt(e.target.value) || 0)}
                              disabled={submitting}
                            />
                          </div>
                        ))}
                        {roles.length === 0 && (
                          <p className="text-sm text-gray-500 col-span-2">Keine Rollen verfügbar. Bitte erstellen Sie zuerst Rollen.</p>
                        )}
                      </div>
                    </div>

                    <Button onClick={createAndSubmit} disabled={submitting || loading} className="w-full">
                      {submitting ? (
                        <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Wird erstellt...</>
                      ) : (
                        <><Send className="h-4 w-4 mr-2" />Schichtplan erstellen & an TiTO senden</>
                      )}
                    </Button>
                  </CardContent>
                </Card>
              )}

              {creationMode === 'manual' && (
                <Card>
                  <CardHeader>
                    <CardTitle>Manuelle Schichtplan-Erstellung</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <Label htmlFor="manualName">Plan-Name</Label>
                      <Input
                        id="manualName"
                        value={manualName}
                        onChange={(e) => setManualName(e.target.value)}
                        placeholder="z.B. April 2026 (manuell)"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="manualStartDate">Startdatum</Label>
                        <Input
                          id="manualStartDate"
                          type="date"
                          value={manualStartDate}
                          onChange={(e) => setManualStartDate(e.target.value)}
                        />
                      </div>
                      <div>
                        <Label htmlFor="manualEndDate">Enddatum</Label>
                        <Input
                          id="manualEndDate"
                          type="date"
                          value={manualEndDate}
                          onChange={(e) => setManualEndDate(e.target.value)}
                        />
                      </div>
                    </div>

                    <div>
                      <Label htmlFor="manualWeekType">Wochen-Typ</Label>
                      <select
                        id="manualWeekType"
                        className="w-full border rounded-md px-3 py-2"
                        value={manualWeekType}
                        onChange={(e) => setManualWeekType(e.target.value as WeekType)}
                      >
                        <option value="A">Woche A</option>
                        <option value="B">Woche B</option>
                      </select>
                    </div>

                    <Button onClick={createManual} className="w-full">
                      <Pen className="h-4 w-4 mr-2" />
                      Schichtplan manuell erstellen
                    </Button>
                  </CardContent>
                </Card>
              )}
            </>
          )}

          {currentScheduleId && submitting && currentScheduleStatus === 'submitted' && (
            <Card>
              <CardContent className="py-12 text-center">
                <Loader2 className="h-12 w-12 mx-auto text-blue-600 mb-4 animate-spin" />
                <p className="text-gray-600 mb-2">Schichtplan wird an TiTO übermittelt</p>
                <p className="text-sm text-gray-500">Die Berechnung kann einige Sekunden dauern...</p>
                <Badge variant="default" className="mt-4">Wird berechnet...</Badge>
              </CardContent>
            </Card>
          )}

          {currentScheduleId && currentScheduleStatus === 'completed' && pollResult && (
            <>
              <Card>
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <CardTitle>{pollResult.name}</CardTitle>
                      <StatusBadge status="completed" />
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => exportShifts(pollResult.shifts, pollResult.name)}
                      >
                        <Download className="h-4 w-4 mr-2" />
                        Exportieren
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setCurrentScheduleId(null);
                          setCurrentScheduleStatus(null);
                          setPollResult(null);
                          setScheduleName('');
                          setStartDate('');
                          setEndDate('');
                          setRoleRequirements({});
                        }}
                      >
                        Neu erstellen
                      </Button>
                    </div>
                  </div>
                </CardHeader>
              </Card>

              <Card>
                <CardHeader>
                  <div className="flex justify-between items-center">
                    <CardTitle>Ergebnis</CardTitle>
                    <Tabs value={currentWeek} onValueChange={(v) => setCurrentWeek(v as WeekType)}>
                      <TabsList>
                        <TabsTrigger value="A">Woche A</TabsTrigger>
                        <TabsTrigger value="B">Woche B</TabsTrigger>
                      </TabsList>
                    </Tabs>
                  </div>
                </CardHeader>
                <CardContent>
                  <ScheduleCalendar
                    shifts={pollResult.shifts}
                    startDate={pollResult.startDate}
                    endDate={pollResult.endDate}
                    currentWeek={currentWeek}
                  />
                </CardContent>
              </Card>
            </>
          )}

          {currentScheduleId && currentScheduleStatus === 'failed' && pollResult && (
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle>{pollResult.name}</CardTitle>
                  <StatusBadge status="failed" />
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-2">
                  <div className="flex items-center gap-2 text-red-800 font-medium">
                    <span className="text-lg">⚠️</span>
                    <span>Berechnung fehlgeschlagen</span>
                  </div>
                  {pollResult.diagnostics && (
                    <p className="text-red-700 text-sm">{pollResult.diagnostics.info}</p>
                  )}
                  {pollResult.metrics?.violations && pollResult.metrics.violations.length > 0 && (
                    <details className="mt-2">
                      <summary className="text-red-600 text-sm cursor-pointer hover:underline">
                        Details ({pollResult.metrics.violations.length} Verletzungen)
                      </summary>
                      <ul className="mt-2 space-y-1">
                        {pollResult.metrics.violations.map((v, i) => (
                          <li key={i} className="text-red-600 text-xs flex items-start gap-1">
                            <span className="mt-0.5 shrink-0">
                              {v.severity === 'HARD' ? '🔴' : '🟡'}
                            </span>
                            <span>{v.message}</span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => handleRetry(pollResult)}>
                    <RotateCcw className="h-4 w-4 mr-1" />
                    Erneut an TiTO senden
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setCurrentScheduleId(null);
                      setCurrentScheduleStatus(null);
                      setPollResult(null);
                      setScheduleName('');
                      setStartDate('');
                      setEndDate('');
                      setRoleRequirements({});
                    }}
                  >
                    Neu erstellen
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {manuallyCreatedSchedule && !currentScheduleId && (
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <CardTitle>{manuallyCreatedSchedule.name}</CardTitle>
                    <StatusBadge status="draft" />
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setManuallyCreatedSchedule(null);
                      setManualName('');
                      setManualStartDate('');
                      setManualEndDate('');
                      setManualWeekType('A');
                    }}
                  >
                    <X className="h-4 w-4 mr-1" />
                    Verwerfen
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <EditableScheduleCalendar
                  schedule={manuallyCreatedSchedule}
                  currentWeek={currentWeek}
                  onUpdateSchedule={(updated) => setManuallyCreatedSchedule(updated)}
                  onSaveShifts={handleManualSave}
                />
              </CardContent>
            </Card>
          )}

          {!currentScheduleId && !submitting && !manuallyCreatedSchedule && creationMode === 'tito' && (
            <Card>
              <CardContent className="py-12 text-center">
                <Calendar className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 mb-2">Noch kein Schichtplan erstellt</p>
                <p className="text-sm text-gray-500">
                  Geben Sie die Einstellungen ein und klicken Sie auf "Schichtplan erstellen & an TiTO senden"
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="manage" className="space-y-6">
          {loading ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Loader2 className="h-8 w-8 mx-auto text-blue-600 mb-4 animate-spin" />
                <p className="text-gray-600">Lade Schichtpläne...</p>
              </CardContent>
            </Card>
          ) : schedules.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <CalendarDays className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 mb-2">Keine gespeicherten Schichtpläne</p>
                <p className="text-sm text-gray-500 mb-4">
                  Erstellen Sie Ihren ersten Schichtplan im Tab "Neu erstellen"
                </p>
                <Button onClick={() => setActiveTab('create')}>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Schichtplan erstellen
                </Button>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {schedules.map((schedule) => (
                  <Card
                    key={schedule.id}
                    className={`transition-all ${
                      selectedSchedule?.id === schedule.id
                        ? 'ring-2 ring-blue-500 shadow-lg'
                        : 'hover:shadow-md'
                    }`}
                  >
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Calendar className="h-5 w-5 text-blue-600" />
                        {schedule.name}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2 text-sm text-gray-600 mb-4">
                        <p>
                          {schedule.startDate ? new Date(schedule.startDate).toLocaleDateString('de-DE') : '-'}
                          {' - '}
                          {schedule.endDate ? new Date(schedule.endDate).toLocaleDateString('de-DE') : '-'}
                        </p>
                        <p>{schedule.shifts.length} Schichten</p>
                        <StatusBadge status={schedule.status || 'draft'} />
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant={selectedSchedule?.id === schedule.id ? "default" : "outline"}
                          onClick={() => handleViewSchedule(schedule)}
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          {selectedSchedule?.id === schedule.id ? 'Ausgewählt' : 'Ansehen'}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleSubmitExisting(schedule)}
                          disabled={submitting}
                        >
                          <Send className="h-4 w-4 mr-1" />
                          TiTO
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => exportShifts(schedule.shifts, schedule.name)}
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleDeleteSchedule(schedule)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {selectedSchedule && (
                <Card>
                  <CardHeader>
                    <div className="flex justify-between items-center">
                      <div className="flex items-center gap-3">
                        <CardTitle>{selectedSchedule.name}</CardTitle>
                        <StatusBadge status={selectedSchedule.status} />
                      </div>
                      <div className="flex items-center gap-2">
                        {selectedSchedule.status === 'failed' && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleRetry(selectedSchedule)}
                          >
                            <RotateCcw className="h-4 w-4 mr-1" />
                            Erneut senden
                          </Button>
                        )}
                        <Tabs value={currentWeek} onValueChange={(v) => setCurrentWeek(v as WeekType)}>
                          <TabsList>
                            <TabsTrigger value="A">Woche A</TabsTrigger>
                            <TabsTrigger value="B">Woche B</TabsTrigger>
                          </TabsList>
                        </Tabs>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {selectedSchedule.status === 'failed' && selectedSchedule.diagnostics && (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-2">
                        <div className="flex items-center gap-2 text-red-800 font-medium">
                          <span className="text-lg">⚠️</span>
                          <span>Berechnung fehlgeschlagen</span>
                        </div>
                        <p className="text-red-700 text-sm">{selectedSchedule.diagnostics.info}</p>
                        {selectedSchedule.metrics?.violations && selectedSchedule.metrics.violations.length > 0 && (
                          <details className="mt-2">
                            <summary className="text-red-600 text-sm cursor-pointer hover:underline">
                              Details ({selectedSchedule.metrics.violations.length} Verletzungen)
                            </summary>
                            <ul className="mt-2 space-y-1">
                              {selectedSchedule.metrics.violations.map((v, i) => (
                                <li key={i} className="text-red-600 text-xs flex items-start gap-1">
                                  <span className="mt-0.5 shrink-0">
                                    {v.severity === 'HARD' ? '🔴' : '🟡'}
                                  </span>
                                  <span>{v.message}</span>
                                </li>
                              ))}
                            </ul>
                          </details>
                        )}
                      </div>
                    )}
                    <EditableScheduleCalendar
                      schedule={selectedSchedule}
                      currentWeek={currentWeek}
                      onUpdateSchedule={handleUpdateSchedule}
                      onSaveShifts={handleManageSave}
                    />
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
