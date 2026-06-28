import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Calendar, Download, Loader2, Send, Pen, X, RotateCcw } from 'lucide-react';
import { Schedule as ScheduleType, WeekType, ShiftTemplateEntry, Employee, Role } from '../../types';
import { ScheduleCalendar } from '../ScheduleCalendar';
import { EditableScheduleCalendar } from '../EditableScheduleCalendar';
import { FairnessMeter } from '../FairnessMeter';
import { toast } from 'sonner';
import * as scheduleService from '../../services/scheduleService';
import * as requestService from '../../services/requestService';
import { scheduleFromResponse } from '../../lib/mappers';
import { exportShiftsCSV } from '../../lib/csv';
import { StatusBadge } from './StatusBadge';
import { ArbZgConfirmDialog } from './ArbZgConfirmDialog';
import type { ArbZgWarning } from '../../types';

interface ScheduleCreateFormProps {
  roles: Role[];
  employees: Employee[];
  loading: boolean;
  addSchedule: (schedule: ScheduleType) => void;
  refresh: () => Promise<void>;
  currentWeek: WeekType;
  setCurrentWeek: (w: WeekType) => void;
  submitting: boolean;
  pollResult: ScheduleType | null;
  currentScheduleId: string | null;
  currentScheduleStatus: string | null;
  setSubmitting: (v: boolean) => void;
  setCurrentScheduleId: (v: string | null) => void;
  setCurrentScheduleStatus: (v: string | null) => void;
  setPollResult: (v: ScheduleType | null) => void;
  onWishReview: (scheduleId: number) => void;
}

export function ScheduleCreateForm({
  roles,
  employees,
  loading,
  addSchedule,
  refresh,
  currentWeek,
  setCurrentWeek,
  submitting,
  pollResult,
  currentScheduleId,
  currentScheduleStatus,
  setSubmitting,
  setCurrentScheduleId,
  setCurrentScheduleStatus,
  setPollResult,
  onWishReview,
}: ScheduleCreateFormProps) {
  const [creationMode, setCreationMode] = useState<'tito' | 'manual'>('tito');
  const [scheduleName, setScheduleName] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [shiftTemplates, setShiftTemplates] = useState<ShiftTemplateEntry[]>([]);
  const [titoWeekType, setTitoWeekType] = useState<WeekType | ''>('A');

  const [manualName, setManualName] = useState('');
  const [manualStartDate, setManualStartDate] = useState('');
  const [manualEndDate, setManualEndDate] = useState('');
  const [manualWeekType, setManualWeekType] = useState<WeekType | ''>('A');
  const [manuallyCreatedSchedule, setManuallyCreatedSchedule] = useState<ScheduleType | null>(null);

  const [arbZgDialogOpen, setArbZgDialogOpen] = useState(false);
  const [arbZgWarnings, setArbZgWarnings] = useState<ArbZgWarning[]>([]);
  const [pendingShiftplans, setPendingShiftplans] = useState<scheduleService.ShiftplanCreateDTO[]>([]);

  // Auto-switch currentWeek when pollResult only contains shifts from one week
  useEffect(() => {
    if (!pollResult || pollResult.shifts.length === 0) return;
    const hasWeekA = pollResult.shifts.some(s => s.week === 'A');
    const hasWeekB = pollResult.shifts.some(s => s.week === 'B');
    if (currentWeek === 'A' && !hasWeekA && hasWeekB) {
      setCurrentWeek('B');
    } else if (currentWeek === 'B' && !hasWeekB && hasWeekA) {
      setCurrentWeek('A');
    }
  }, [pollResult, currentWeek, setCurrentWeek]);

  const resetCreateState = () => {
    setCurrentScheduleId(null);
    setCurrentScheduleStatus(null);
    setPollResult(null);
    setScheduleName('');
    setStartDate('');
    setEndDate('');
    setShiftTemplates([]);
    setTitoWeekType('A');
  };

  const addShiftTemplate = () => {
    const id = `shift_${Date.now()}`;
    setShiftTemplates(prev => [...prev, {
      id,
      name: '',
      startTime: '06:00',
      endTime: '14:00',
      requirements: {},
    }]);
  };

  const removeShiftTemplate = (index: number) => {
    setShiftTemplates(prev => prev.filter((_, i) => i !== index));
  };

  const updateShiftTemplate = (index: number, field: string, value: string | Record<string, number>) => {
    setShiftTemplates(prev => prev.map((st, i) =>
      i === index ? { ...st, [field]: value } : st
    ));
  };

  const updateRequirement = (templateIndex: number, roleId: string, count: number) => {
    setShiftTemplates(prev => prev.map((st, i) =>
      i === templateIndex
        ? { ...st, requirements: { ...st.requirements, [roleId]: count } }
        : st
    ));
  };

  const createAndSubmit = async () => {
    if (!scheduleName || !startDate || !endDate) {
      toast.error('Bitte Name, Start- und Enddatum eingeben');
      return;
    }
    if (shiftTemplates.length === 0 || shiftTemplates.some(st => !st.name || !st.startTime || !st.endTime)) {
      toast.error('Bitte mindestens ein vollständiges Schicht-Template definieren');
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
        week_type: titoWeekType || undefined,
        shift_templates: shiftTemplates.map(st => ({
          ...st,
          requirements: Object.fromEntries(
            Object.entries(st.requirements).filter(([, count]) => count > 0)
          ),
        })),
        shiftplans: [],
      });

      const mapped = scheduleFromResponse(created);
      addSchedule(mapped);

      try {
        const pending = await requestService.getPendingShiftWishes(created.id);
        if (pending.items.length > 0) {
          onWishReview(created.id);
          return;
        }
      } catch {
        // If the endpoint fails, just proceed
      }

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
        week_type: manualWeekType || undefined,
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

    try {
      const result = await scheduleService.replaceAllShifts(Number(manuallyCreatedSchedule.id), shiftplans);
      if (result.arbZgWarnings && result.arbZgWarnings.length > 0) {
        setPendingShiftplans(shiftplans);
        setArbZgWarnings(result.arbZgWarnings);
        setArbZgDialogOpen(true);
        return;
      }
      finalizeManualSave();
    } catch {
      toast.error('Fehler beim Speichern des Schichtplans');
    }
  };

  const finalizeManualSave = async () => {
    await refresh();
    setManuallyCreatedSchedule(null);
    setManualName('');
    setManualStartDate('');
    setManualEndDate('');
    setManualWeekType('A');
    setCreationMode('tito');
    setArbZgDialogOpen(false);
    setArbZgWarnings([]);
    setPendingShiftplans([]);
    toast.success('Schichtplan gespeichert');
  };

  const handleConfirmArbZg = async () => {
    if (!manuallyCreatedSchedule || pendingShiftplans.length === 0) return;
    try {
      await scheduleService.replaceAllShifts(Number(manuallyCreatedSchedule.id), pendingShiftplans);
      finalizeManualSave();
    } catch {
      toast.error('Fehler beim Speichern des Schichtplans');
    }
  };

  const handleChangeStatus = async (schedule: ScheduleType, newStatus: string) => {
    const updated = { ...schedule, status: newStatus };
    setManuallyCreatedSchedule(updated);
    try {
      await scheduleService.updateSchedule(Number(schedule.id), { status: newStatus });
      toast.success('Status geändert');
    } catch {
      toast.error('Fehler beim Ändern des Status');
      setManuallyCreatedSchedule(schedule);
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
      toast.error('Fehler beim erneutem Senden');
    }
  };

  // --- Submitting indicator ---
  if (currentScheduleId && submitting && currentScheduleStatus === 'submitted') {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Loader2 className="h-12 w-12 mx-auto text-blue-600 mb-4 animate-spin" />
          <p className="text-gray-600 mb-2">Schichtplan wird an TiTO übermittelt</p>
          <p className="text-sm text-gray-500">Die Berechnung kann einige Sekunden dauern...</p>
          <StatusBadge status="submitted" />
        </CardContent>
      </Card>
    );
  }

  // --- Completed result ---
  if (currentScheduleId && currentScheduleStatus === 'completed' && pollResult) {
    return (
      <>
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center gap-3">
              <div className="flex items-center gap-3 flex-wrap">
                <CardTitle>{pollResult.name}</CardTitle>
                <StatusBadge status="completed" />
              </div>
              <div className="flex gap-2 flex-wrap">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => exportShiftsCSV(pollResult.shifts, pollResult.name, employees)}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Exportieren
                </Button>
                <Button variant="outline" size="sm" onClick={resetCreateState}>
                  Neu erstellen
                </Button>
              </div>
            </div>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Ergebnis</CardTitle>
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

        {pollResult.metrics?.employeeFairness && (
          <FairnessMeter
            employees={employees}
            roles={roles}
            employeeFairness={pollResult.metrics.employeeFairness}
          />
        )}
      </>
    );
  }

  // --- Failed result ---
  if (currentScheduleId && currentScheduleStatus === 'failed' && pollResult) {
    return (
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start gap-2">
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
            <Button variant="outline" onClick={resetCreateState}>
              Neu erstellen
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // --- Manually created schedule editor ---
  if (manuallyCreatedSchedule && !currentScheduleId) {
    return (
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-start gap-3">
            <div className="flex items-center gap-3 flex-wrap">
              <CardTitle>{manuallyCreatedSchedule.name}</CardTitle>
              <StatusBadge status={manuallyCreatedSchedule.status} />
              {manuallyCreatedSchedule.status === 'draft' && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleChangeStatus(manuallyCreatedSchedule, 'review')}
                >
                  In Prüfung geben
                </Button>
              )}
              {manuallyCreatedSchedule.status === 'review' && (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleChangeStatus(manuallyCreatedSchedule, 'draft')}
                  >
                    Bearbeiten
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleChangeStatus(manuallyCreatedSchedule, 'completed')}
                  >
                    Abschließen
                  </Button>
                </>
              )}
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
          {manuallyCreatedSchedule.status === 'draft' ? (
            <EditableScheduleCalendar
              schedule={manuallyCreatedSchedule}
              currentWeek={currentWeek}
              onUpdateSchedule={(updated) => setManuallyCreatedSchedule(updated)}
              onSaveShifts={handleManualSave}
            />
          ) : (
            <ScheduleCalendar
              shifts={manuallyCreatedSchedule.shifts}
              startDate={manuallyCreatedSchedule.startDate}
              endDate={manuallyCreatedSchedule.endDate}
              currentWeek={currentWeek}
            />
          )}
        </CardContent>
      </Card>
    );
  }

  // --- Default: creation forms ---
  return (
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

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Schicht-Templates</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addShiftTemplate}
                  disabled={submitting}
                >
                  <Calendar className="h-4 w-4 mr-1" />
                  Schicht hinzufügen
                </Button>
              </div>

              {shiftTemplates.length === 0 && (
                <p className="text-sm text-gray-500">
                  Keine Schichten definiert. Klicken Sie auf "Schicht hinzufügen", um eine zu erstellen.
                </p>
              )}

              <div className="space-y-3">
                {shiftTemplates.map((st, index) => (
                  <div key={st.id} className="border rounded-lg p-4 space-y-3">
                    <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                      <div>
                        <Label className="text-xs">Name</Label>
                        <Input
                          value={st.name}
                          onChange={(e) => updateShiftTemplate(index, 'name', e.target.value)}
                          placeholder="z.B. Frühschicht"
                          disabled={submitting}
                        />
                      </div>
                      <div>
                        <Label className="text-xs">Startzeit</Label>
                        <Input
                          type="time"
                          value={st.startTime}
                          onChange={(e) => updateShiftTemplate(index, 'startTime', e.target.value)}
                          disabled={submitting}
                        />
                      </div>
                      <div>
                        <Label className="text-xs">Endzeit</Label>
                        <Input
                          type="time"
                          value={st.endTime}
                          onChange={(e) => updateShiftTemplate(index, 'endTime', e.target.value)}
                          disabled={submitting}
                        />
                      </div>
                      <div className="flex items-end">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeShiftTemplate(index)}
                          disabled={submitting}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>

                    <div>
                      <Label className="text-xs">Rollen-Anforderungen pro Tag</Label>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-1">
                        {roles.map(role => (
                          <div key={role.id} className="flex items-center gap-2">
                            <div
                              className="w-2 h-2 rounded-full shrink-0"
                              style={{ backgroundColor: role.color }}
                            />
                            <span className="text-xs truncate">{role.name}</span>
                            <Input
                              type="number"
                              min="0"
                              value={st.requirements[role.id] || 0}
                              onChange={(e) => updateRequirement(index, role.id, parseInt(e.target.value) || 0)}
                              className="w-16 h-8 text-xs"
                              disabled={submitting}
                            />
                          </div>
                        ))}
                        {roles.length === 0 && (
                          <p className="text-xs text-gray-500 col-span-full">
                            Keine Rollen vorhanden. Erstellen Sie zuerst Rollen.
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <Label htmlFor="titoWeekType">Wochen-Typ</Label>
              <select
                id="titoWeekType"
                className="w-full border rounded-md px-3 py-2"
                value={titoWeekType}
                onChange={(e) => setTitoWeekType(e.target.value as WeekType | '')}
                disabled={submitting}
              >
                <option value="A">Nur Woche A</option>
                <option value="B">Nur Woche B</option>
                <option value="">Beide (A & B)</option>
              </select>
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

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
                onChange={(e) => setManualWeekType(e.target.value as WeekType | '')}
              >
                <option value="A">Nur Woche A</option>
                <option value="B">Nur Woche B</option>
                <option value="">Beide (A & B)</option>
              </select>
            </div>

            <Button onClick={createManual} className="w-full">
              <Pen className="h-4 w-4 mr-2" />
              Schichtplan manuell erstellen
            </Button>
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

      <ArbZgConfirmDialog
        open={arbZgDialogOpen}
        warnings={arbZgWarnings}
        onConfirm={handleConfirmArbZg}
        onCancel={() => setArbZgDialogOpen(false)}
      />
    </>
  );
}
