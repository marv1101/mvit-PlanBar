import { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../ui/alert-dialog';
import { Tabs, TabsList, TabsTrigger } from '../ui/tabs';
import {
  Calendar,
  CalendarDays,
  Download,
  Eye,
  FileText,
  FileUp,
  Trash2,
  Loader2,
  Send,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from '../ui/dropdown-menu';
import { Schedule as ScheduleType, WeekType, Employee, Role } from '../../types';
import { ScheduleCalendar } from '../ScheduleCalendar';
import { EditableScheduleCalendar } from '../EditableScheduleCalendar';
import { FairnessMeter } from '../FairnessMeter';
import { toast } from 'sonner';
import * as scheduleService from '../../services/scheduleService';
import * as requestService from '../../services/requestService';
import { scheduleFromResponse } from '../../lib/mappers';
import { getWeekType } from '../../lib/week';
import { TIMEZONE } from '../../lib/timezone';
import { exportShiftsCSV } from '../../lib/csv';
import { StatusBadge } from './StatusBadge';
import { ArbZgConfirmDialog } from './ArbZgConfirmDialog';
import type { ArbZgWarning } from '../../types';

interface ScheduleManageListProps {
  schedules: ScheduleType[];
  loading: boolean;
  employees: Employee[];
  roles: Role[];
  currentWeek: WeekType;
  setCurrentWeek: (w: WeekType) => void;
  refresh: () => Promise<void>;
  submitting: boolean;
  deleteSchedule: (id: string) => void;
  updateSchedule: (id: string, schedule: ScheduleType) => void;
  onWishReview: (scheduleId: number) => void;
  setCurrentScheduleId: (v: string | null) => void;
  setCurrentScheduleStatus: (v: string | null) => void;
  onCreateTab: () => void;
}

export function ScheduleManageList({
  schedules,
  loading,
  employees,
  roles,
  currentWeek,
  setCurrentWeek,
  refresh,
  submitting,
  deleteSchedule,
  updateSchedule,
  onWishReview,
  setCurrentScheduleId,
  setCurrentScheduleStatus,
  onCreateTab,
}: ScheduleManageListProps) {
  const [selectedSchedule, setSelectedSchedule] = useState<ScheduleType | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ScheduleType | null>(null);
  const [arbZgDialogOpen, setArbZgDialogOpen] = useState(false);
  const [arbZgWarnings, setArbZgWarnings] = useState<ArbZgWarning[]>([]);
  const [pendingShiftplans, setPendingShiftplans] = useState<scheduleService.ShiftplanCreateDTO[]>([]);

  const rangeWeeks = useMemo(() => {
    const weeks = new Set<WeekType>();
    if (!selectedSchedule?.startDate || !selectedSchedule?.endDate) return weeks;
    const end = new Date(`${selectedSchedule.endDate}T00:00:00Z`);
    for (let d = new Date(`${selectedSchedule.startDate}T00:00:00Z`); d <= end; d.setUTCDate(d.getUTCDate() + 1)) {
      weeks.add(getWeekType(d));
    }
    return weeks;
  }, [selectedSchedule]);
  const scope = selectedSchedule?.weekType ?? null;
  const hasWeekA = scope ? scope === 'A' : rangeWeeks.has('A');
  const hasWeekB = scope ? scope === 'B' : rangeWeeks.has('B');
  const showTabs = hasWeekA || hasWeekB;

  useEffect(() => {
    if (!selectedSchedule) return;
    if (currentWeek === 'A' && !hasWeekA && hasWeekB) {
      setCurrentWeek('B');
    } else if (currentWeek === 'B' && !hasWeekB && hasWeekA) {
      setCurrentWeek('A');
    }
  }, [selectedSchedule, currentWeek, setCurrentWeek, hasWeekA, hasWeekB]);

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
      const pending = await requestService.getPendingShiftWishes(Number(schedule.id));
      if (pending.items.length > 0) {
        onWishReview(Number(schedule.id));
        return;
      }
    } catch {
      // If the endpoint fails, just proceed
    }

    doSubmitExisting(schedule);
  };

  const doSubmitExisting = async (schedule: ScheduleType) => {
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
    setDeleteTarget(schedule);
  };

  const handleExportPdf = async (schedule: ScheduleType) => {
    try {
      await scheduleService.downloadSchedulePdf(Number(schedule.id), schedule.name);
      toast.success('PDF exportiert');
    } catch {
      toast.error('Fehler beim PDF-Export');
    }
  };

  const handleExportIcal = async (schedule: ScheduleType) => {
    try {
      await scheduleService.downloadScheduleIcal(Number(schedule.id), schedule.name);
      toast.success('iCal-Datei exportiert');
    } catch {
      toast.error('Fehler beim iCal-Export');
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
      break_start: s.breakStart,
      break_end: s.breakEnd,
    }));

    try {
      const result = await scheduleService.replaceAllShifts(Number(selectedSchedule.id), shiftplans);
      if (result.arbZgWarnings && result.arbZgWarnings.length > 0) {
        setPendingShiftplans(shiftplans);
        setArbZgWarnings(result.arbZgWarnings);
        setArbZgDialogOpen(true);
        return;
      }
      finalizeManageSave(shifts);
    } catch {
      toast.error('Fehler beim Speichern des Schichtplans');
    }
  };

  const finalizeManageSave = async (shifts: ScheduleType['shifts']) => {
    await refresh();
    setSelectedSchedule(prev => prev ? { ...prev, shifts } : null);
    setArbZgDialogOpen(false);
    setArbZgWarnings([]);
    setPendingShiftplans([]);
    toast.success('Schichtplan gespeichert');
  };

  const handleConfirmArbZg = async () => {
    if (!selectedSchedule || pendingShiftplans.length === 0) return;
    try {
      await scheduleService.replaceAllShifts(Number(selectedSchedule.id), pendingShiftplans);
      finalizeManageSave(selectedSchedule.shifts);
    } catch {
      toast.error('Fehler beim Speichern des Schichtplans');
    }
  };

  const handleUpdateSchedule = (updatedSchedule: ScheduleType) => {
    updateSchedule(updatedSchedule.id, updatedSchedule);
    setSelectedSchedule(updatedSchedule);
  };

  const handleChangeStatus = (schedule: ScheduleType, newStatus: string) => {
    const updated = { ...schedule, status: newStatus };
    updateSchedule(schedule.id, updated);
    setSelectedSchedule(updated);
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Loader2 className="h-8 w-8 mx-auto text-blue-600 mb-4 animate-spin" />
          <p className="text-gray-600">Lade Schichtpläne...</p>
        </CardContent>
      </Card>
    );
  }

  if (schedules.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <CalendarDays className="h-12 w-12 mx-auto text-gray-400 mb-4" />
          <p className="text-gray-600 mb-2">Keine gespeicherten Schichtpläne</p>
          <p className="text-sm text-gray-500 mb-4">
            Erstellen Sie Ihren ersten Schichtplan im Tab "Neu erstellen"
          </p>
          <Button onClick={onCreateTab}>
            <Sparkles className="h-4 w-4 mr-2" />
            Schichtplan erstellen
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
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
                  {schedule.startDate ? new Date(schedule.startDate).toLocaleDateString('de-DE', { timeZone: TIMEZONE }) : '-'}
                  {' - '}
                  {schedule.endDate ? new Date(schedule.endDate).toLocaleDateString('de-DE', { timeZone: TIMEZONE }) : '-'}
                </p>
                <p>{schedule.shifts.length} Schichten</p>
                <div className="flex items-center gap-2 flex-wrap">
                  <StatusBadge status={schedule.status || 'draft'} />
                  {schedule.weekType && (
                    <Badge variant="outline">Nur Woche {schedule.weekType}</Badge>
                  )}
                </div>
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
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      size="sm"
                      variant="outline"
                      aria-label="Exportieren"
                    >
                      <Download className="h-4 w-4 mr-1" />
                      Export
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => handleExportPdf(schedule)}>
                      <FileText className="mr-2 h-4 w-4" />
                      PDF
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleExportIcal(schedule)}>
                      <FileUp className="mr-2 h-4 w-4" />
                      iCal
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => exportShiftsCSV(schedule.shifts, schedule.name, employees)}>
                      <Download className="mr-2 h-4 w-4" />
                      CSV
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => handleDeleteSchedule(schedule)}
                  aria-label="Schichtplan löschen"
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
            <div className="flex flex-col lg:flex-row lg:items-center gap-3">
              <div className="flex items-center gap-3 flex-wrap">
                <CardTitle>{selectedSchedule.name}</CardTitle>
                <StatusBadge status={selectedSchedule.status} />
                {selectedSchedule.weekType && (
                  <Badge variant="outline">Nur Woche {selectedSchedule.weekType}</Badge>
                )}
                {selectedSchedule.status === 'draft' && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleChangeStatus(selectedSchedule, 'review')}
                  >
                    In Prüfung geben
                  </Button>
                )}
                {selectedSchedule.status === 'review' && (
                  <>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleChangeStatus(selectedSchedule, 'draft')}
                    >
                      Bearbeiten
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleChangeStatus(selectedSchedule, 'completed')}
                    >
                      Abschließen
                    </Button>
                  </>
                )}
                {selectedSchedule.status === 'completed' && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleChangeStatus(selectedSchedule, 'draft')}
                  >
                    Bearbeiten
                  </Button>
                )}
                {selectedSchedule.status === 'failed' && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleChangeStatus(selectedSchedule, 'draft')}
                  >
                    Wieder öffnen
                  </Button>
                )}
              </div>
              <div className="flex items-center gap-2 flex-wrap">
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
                {showTabs && (
                  <Tabs value={currentWeek} onValueChange={(v) => setCurrentWeek(v as WeekType)}>
                    <TabsList>
                      {hasWeekA && <TabsTrigger value="A">Woche A</TabsTrigger>}
                      {hasWeekB && <TabsTrigger value="B">Woche B</TabsTrigger>}
                    </TabsList>
                  </Tabs>
                )}
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
            {selectedSchedule.status === 'draft' ? (
              <EditableScheduleCalendar
                schedule={selectedSchedule}
                currentWeek={currentWeek}
                onUpdateSchedule={handleUpdateSchedule}
                onSaveShifts={handleManageSave}
              />
            ) : selectedSchedule.shifts.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12 text-gray-500">
                  <Calendar className="h-12 w-12 mb-4 opacity-50" />
                  <p className="text-lg font-medium">Keine Schichten vorhanden</p>
                  <p className="text-sm">Für diesen Schichtplan sind keine Schichten geplant.</p>
                </CardContent>
              </Card>
            ) : (
              <>
                <ScheduleCalendar
                  shifts={selectedSchedule.shifts}
                  startDate={selectedSchedule.startDate}
                  endDate={selectedSchedule.endDate}
                  currentWeek={currentWeek}
                />
                {selectedSchedule.metrics?.employeeFairness && (
                  <div className="mt-4">
                    <FairnessMeter
                      employees={employees}
                      roles={roles}
                      employeeFairness={selectedSchedule.metrics.employeeFairness}
                    />
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}

      <AlertDialog open={deleteTarget !== null} onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Schichtplan löschen</AlertDialogTitle>
            <AlertDialogDescription>
              Möchten Sie den Schichtplan „{deleteTarget?.name}" wirklich löschen?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Abbrechen</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (deleteTarget) {
                  deleteSchedule(deleteTarget.id);
                  if (selectedSchedule?.id === deleteTarget.id) {
                    setSelectedSchedule(null);
                  }
                  setDeleteTarget(null);
                }
              }}
            >
              Löschen
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <ArbZgConfirmDialog
        open={arbZgDialogOpen}
        warnings={arbZgWarnings}
        onConfirm={handleConfirmArbZg}
        onCancel={() => setArbZgDialogOpen(false)}
      />
    </>
  );
}
