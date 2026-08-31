import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Download, Loader2, Send, Pen, X, RotateCcw } from 'lucide-react';
import { Schedule as ScheduleType, WeekType, Employee, Role } from '../../types';
import { ScheduleCalendar } from '../ScheduleCalendar';
import { EditableScheduleCalendar } from '../EditableScheduleCalendar';
import { FairnessMeter } from '../FairnessMeter';
import { toast } from 'sonner';
import * as scheduleService from '../../services/scheduleService';
import * as requestService from '../../services/requestService';
import { exportShiftsCSV } from '../../lib/csv';
import { weekTypeOfDateStr } from '../../lib/week';
import { StatusBadge } from './StatusBadge';
import { ArbZgConfirmDialog } from './ArbZgConfirmDialog';
import type { ArbZgWarning } from '../../types';
import { useScheduleForm } from '../../hooks/useScheduleForm';
import { useManualScheduleForm } from '../../hooks/useManualScheduleForm';
import { TitoScheduleForm } from './ScheduleCreateForm/TitoScheduleForm';
import { ManualScheduleForm } from './ScheduleCreateForm/ManualScheduleForm';

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
  const titoForm = useScheduleForm();
  const manualForm = useManualScheduleForm();

  const [arbZgDialogOpen, setArbZgDialogOpen] = useState(false);
  const [arbZgWarnings, setArbZgWarnings] = useState<ArbZgWarning[]>([]);
  const [pendingShiftplans, setPendingShiftplans] = useState<scheduleService.ShiftplanCreateDTO[]>([]);

  // Auto-switch currentWeek when pollResult only contains shifts from one week
  useEffect(() => {
    if (!pollResult || pollResult.shifts.length === 0) return;
    const hasWeekA = pollResult.shifts.some(s => weekTypeOfDateStr(s.date) === 'A');
    const hasWeekB = pollResult.shifts.some(s => weekTypeOfDateStr(s.date) === 'B');
    if (currentWeek === 'A' && !hasWeekA && hasWeekB) {
      setCurrentWeek('B');
    } else if (currentWeek === 'B' && !hasWeekB && hasWeekA) {
      setCurrentWeek('A');
    }
  }, [pollResult, currentWeek, setCurrentWeek]);

  const resetCreateState = useCallback(() => {
    setCurrentScheduleId(null);
    setCurrentScheduleStatus(null);
    setPollResult(null);
    titoForm.reset();
  }, [setCurrentScheduleId, setCurrentScheduleStatus, setPollResult, titoForm.reset]);

  const handleTitoSubmit = useCallback(async () => {
    setSubmitting(true);
    setPollResult(null);
    setCurrentScheduleId(null);
    setCurrentScheduleStatus(null);

    try {
      const created = await titoForm.submit();
      if (!created) {
        setSubmitting(false);
        return;
      }

      addSchedule(created);

      try {
        const pending = await requestService.getPendingShiftWishes(Number(created.id));
        if (pending.items.length > 0) {
          onWishReview(Number(created.id));
          return;
        }
      } catch {
        // If the endpoint fails, just proceed
      }

      setCurrentScheduleId(created.id);
      setCurrentScheduleStatus('submitted');

      const submitted = await scheduleService.submitScheduleToTito(Number(created.id));
      setCurrentScheduleStatus(submitted.status);
      toast.success('Schichtplan an TiTO übermittelt');
    } catch {
      setSubmitting(false);
      setCurrentScheduleId(null);
      setCurrentScheduleStatus(null);
      toast.error('Fehler beim Erstellen oder Übermitteln des Schichtplans');
    }
  }, [titoForm.submit, addSchedule, onWishReview, setCurrentScheduleId, setCurrentScheduleStatus, setPollResult, setSubmitting]);

  const handleManualSubmit = useCallback(async () => {
    try {
      const created = await manualForm.submit();
      if (created) {
        addSchedule(created);
        toast.success('Schichtplan erstellt');
      }
    } catch {
      toast.error('Fehler beim Erstellen des Schichtplans');
    }
  }, [manualForm.submit, addSchedule]);

  const handleManualSave = useCallback(async (shifts: ScheduleType['shifts']): Promise<void> => {
    if (!manualForm.manuallyCreatedSchedule) return;
    const shiftplans = shifts.map(s => ({
      employee_id: Number(s.employeeId),
      date: s.date,
      shift_id: s.id,
      start_time: s.startTime,
      end_time: s.endTime,
      break_start: s.breakStart,
      break_end: s.breakEnd,
    }));

    try {
      const result = await scheduleService.replaceAllShifts(Number(manualForm.manuallyCreatedSchedule.id), shiftplans);
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
  }, [manualForm.manuallyCreatedSchedule]);

  const finalizeManualSave = useCallback(async () => {
    await refresh();
    manualForm.reset();
    setCreationMode('tito');
    setArbZgDialogOpen(false);
    setArbZgWarnings([]);
    setPendingShiftplans([]);
    toast.success('Schichtplan gespeichert');
  }, [refresh, manualForm.reset]);

  const handleConfirmArbZg = useCallback(async () => {
    if (!manualForm.manuallyCreatedSchedule || pendingShiftplans.length === 0) return;
    try {
      await scheduleService.replaceAllShifts(Number(manualForm.manuallyCreatedSchedule.id), pendingShiftplans);
      finalizeManualSave();
    } catch {
      toast.error('Fehler beim Speichern des Schichtplans');
    }
  }, [manualForm.manuallyCreatedSchedule, pendingShiftplans, finalizeManualSave]);

  const handleChangeStatus = useCallback(async (schedule: ScheduleType, newStatus: string) => {
    const updated = { ...schedule, status: newStatus };
    manualForm.setManuallyCreatedSchedule(updated);
    try {
      await scheduleService.updateSchedule(Number(schedule.id), { status: newStatus });
      toast.success('Status geändert');
    } catch {
      toast.error('Fehler beim Ändern des Status');
      manualForm.setManuallyCreatedSchedule(schedule);
    }
  }, [manualForm.setManuallyCreatedSchedule]);

  const handleRetry = useCallback(async (schedule: ScheduleType) => {
    try {
      await scheduleService.retrySchedule(Number(schedule.id));
      toast.success('Schichtplan wird erneut an TiTO gesendet');
      refresh();
      setCurrentScheduleId(schedule.id);
      setCurrentScheduleStatus('submitted');
    } catch {
      toast.error('Fehler beim erneutem Senden');
    }
  }, [refresh, setCurrentScheduleId, setCurrentScheduleStatus]);

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
  if (manualForm.manuallyCreatedSchedule && !currentScheduleId) {
    return (
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-start gap-3">
            <div className="flex items-center gap-3 flex-wrap">
              <CardTitle>{manualForm.manuallyCreatedSchedule.name}</CardTitle>
              <StatusBadge status={manualForm.manuallyCreatedSchedule.status} />
              {manualForm.manuallyCreatedSchedule.status === 'draft' && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleChangeStatus(manualForm.manuallyCreatedSchedule!, 'review')}
                >
                  In Prüfung geben
                </Button>
              )}
              {manualForm.manuallyCreatedSchedule.status === 'review' && (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleChangeStatus(manualForm.manuallyCreatedSchedule!, 'draft')}
                  >
                    Bearbeiten
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleChangeStatus(manualForm.manuallyCreatedSchedule!, 'completed')}
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
                manualForm.reset();
              }}
            >
              <X className="h-4 w-4 mr-1" />
              Verwerfen
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {manualForm.manuallyCreatedSchedule.status === 'draft' ? (
            <EditableScheduleCalendar
              schedule={manualForm.manuallyCreatedSchedule}
              currentWeek={currentWeek}
              onUpdateSchedule={(updated) => manualForm.setManuallyCreatedSchedule(updated)}
              onSaveShifts={handleManualSave}
            />
          ) : (
            <ScheduleCalendar
              shifts={manualForm.manuallyCreatedSchedule.shifts}
              startDate={manualForm.manuallyCreatedSchedule.startDate}
              endDate={manualForm.manuallyCreatedSchedule.endDate}
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
          <CardContent>
            <TitoScheduleForm
              roles={roles}
              shiftTemplates={titoForm.shiftTemplates}
              titoWeekType={titoForm.titoWeekType}
              setTitoWeekType={titoForm.setTitoWeekType}
              addShiftTemplate={titoForm.addShiftTemplate}
              removeShiftTemplate={titoForm.removeShiftTemplate}
              updateShiftTemplate={titoForm.updateShiftTemplate}
              updateRequirement={titoForm.updateRequirement}
              updateMaxRequirement={titoForm.updateMaxRequirement}
              maximizeStaffing={titoForm.maximizeStaffing}
              setMaximizeStaffing={titoForm.setMaximizeStaffing}
              scheduleName={titoForm.scheduleName}
              setScheduleName={titoForm.setScheduleName}
              startDate={titoForm.startDate}
              setStartDate={titoForm.setStartDate}
              endDate={titoForm.endDate}
              setEndDate={titoForm.setEndDate}
              creating={titoForm.loading}
              submitting={titoForm.submitting}
            />
            <Button 
              onClick={handleTitoSubmit} 
              disabled={titoForm.submitting || loading || !titoForm.canSubmit} 
              className="w-full mt-4"
            >
              {titoForm.submitting ? (
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
          <CardContent>
            <ManualScheduleForm
              manualName={manualForm.manualName}
              setManualName={manualForm.setManualName}
              manualStartDate={manualForm.manualStartDate}
              setManualStartDate={manualForm.setManualStartDate}
              manualEndDate={manualForm.manualEndDate}
              setManualEndDate={manualForm.setManualEndDate}
              manualWeekType={manualForm.manualWeekType}
              setManualWeekType={manualForm.setManualWeekType}
              manuallyCreatedSchedule={manualForm.manuallyCreatedSchedule}
              submitting={manualForm.submitting}
              creating={manualForm.loading}
              onSubmit={handleManualSubmit}
              onReset={() => manualForm.reset()}
            />
          </CardContent>
        </Card>
      )}

      {!currentScheduleId && !submitting && !manualForm.manuallyCreatedSchedule && creationMode === 'tito' && (
        <Card>
          <CardContent className="py-12 text-center">
            <Send className="h-12 w-12 mx-auto text-gray-400 mb-4" />
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
