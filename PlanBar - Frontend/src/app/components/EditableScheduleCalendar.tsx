import React, { useMemo, useState, useRef } from 'react';
import { useDrag, useDrop, DndProvider } from 'react-dnd';
import { TouchBackend } from 'react-dnd-touch-backend';
import { useApp } from '../context/AppContext';
import { Shift, Schedule, WeekType } from '../types';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Button } from './ui/button';
import { Checkbox } from './ui/checkbox';
import { getWeekType } from '../lib/week';
import { useMediaQuery } from '../lib/useMediaQuery';
import { TIMEZONE } from '../lib/timezone';
import { ShiftListView } from './ShiftListView';
import { Pencil, Trash2, Users, Save, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import type { Employee } from '../types';

const ITEM_TYPE = 'SHIFT';
const EMPLOYEE_ITEM_TYPE = 'EMPLOYEE';
const HOUR_HEIGHT = 52;
const START_HOUR = 6;
const END_HOUR = 22;

const HOURS = Array.from({ length: END_HOUR - START_HOUR }, (_, i) => START_HOUR + i);

interface DragItem {
  shift: Shift;
  fromDate: string;
}

interface EmployeeDragItem {
  employeeId: string;
}

interface EditableScheduleCalendarProps {
  schedule: Schedule;
  currentWeek: WeekType;
  onUpdateSchedule: (schedule: Schedule) => void;
  onSaveShifts?: (shifts: Shift[]) => Promise<void>;
}

function toMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number);
  return h * 60 + m;
}

function formatTime(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function assignLanes(shifts: Shift[]): { shift: Shift; lane: number; totalLanes: number }[] {
  const sorted = [...shifts].sort((a, b) => toMinutes(a.startTime) - toMinutes(b.startTime));
  const lanes: number[] = [];
  const result: { shift: Shift; lane: number }[] = [];

  for (const shift of sorted) {
    const start = toMinutes(shift.startTime);
    const end = toMinutes(shift.endTime);
    let assigned = false;

    for (let i = 0; i < lanes.length; i++) {
      if (lanes[i] <= start) {
        lanes[i] = end;
        result.push({ shift, lane: i });
        assigned = true;
        break;
      }
    }

    if (!assigned) {
      lanes.push(end);
      result.push({ shift, lane: lanes.length - 1 });
    }
  }

  return result.map(r => ({ ...r, totalLanes: lanes.length }));
}

function getShiftStyle(shift: Shift, lane: number, totalLanes: number) {
  const startMin = toMinutes(shift.startTime);
  const endMin = toMinutes(shift.endTime);
  const rangeStart = START_HOUR * 60;
  const top = ((startMin - rangeStart) / 60) * HOUR_HEIGHT;
  const height = Math.max(((endMin - startMin) / 60) * HOUR_HEIGHT, 24);
  const width = 100 / totalLanes;
  const left = lane * width;

  return {
    top: `${top}px`,
    height: `${height}px`,
    left: `${left}%`,
    width: `${width}%`,
  };
}

interface ShiftBarProps {
  shift: Shift;
  lane: number;
  totalLanes: number;
  onEdit: (shift: Shift) => void;
  onDelete: (shift: Shift) => void;
}

function ShiftBar({ shift, lane, totalLanes, onEdit, onDelete }: ShiftBarProps) {
  const { employees } = useApp();
  const employee = employees.find(e => e.id === shift.employeeId);

  const [{ isDragging }, drag] = useDrag(() => ({
    type: ITEM_TYPE,
    item: { shift, fromDate: shift.date } as DragItem,
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  }), [shift]);

  if (!employee) return null;

  const style = getShiftStyle(shift, lane, totalLanes);
  const showTime = totalLanes <= 2;

  return (
    <div
      ref={drag}
      className={`absolute rounded overflow-hidden cursor-move group z-10 ${
        isDragging ? 'opacity-50' : ''
      }`}
      style={{
        ...style,
        position: 'absolute',
        backgroundColor: employee.color + '20',
        borderLeft: `3px solid ${employee.color}`,
      }}
      onClick={(e) => {
        e.stopPropagation();
        onEdit(shift);
      }}
    >
      <div className="flex flex-col justify-center h-full px-1.5 py-0.5 text-[11px] leading-tight">
        <span className="font-medium truncate flex items-center gap-1" style={{ color: employee.color }}>
          <span className={`inline-flex items-center justify-center w-3.5 h-3.5 rounded text-[9px] font-bold leading-none ${
            shift.week === 'A' ? 'bg-blue-500 text-white' : 'bg-purple-500 text-white'
          }`}>
            {shift.week}
          </span>
          {employee.name}
        </span>
        {showTime && (
          <span className="text-gray-500 truncate">
            {shift.startTime}–{shift.endTime}
          </span>
        )}
      </div>
      <div className="absolute top-0.5 right-0.5 flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={(e) => { e.stopPropagation(); onEdit(shift); }}
          className="p-0.5 hover:bg-gray-200 rounded bg-white/80"
          aria-label={`Schicht ${employee.name} ${shift.startTime}–${shift.endTime} bearbeiten`}
        >
          <Pencil className="h-2.5 w-2.5" />
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(shift); }}
          className="p-0.5 hover:bg-red-100 rounded text-red-600 bg-white/80"
          aria-label={`Schicht ${employee.name} ${shift.startTime}–${shift.endTime} löschen`}
        >
          <Trash2 className="h-2.5 w-2.5" />
        </button>
      </div>
    </div>
  );
}

function EmployeeCard({ employee }: { employee: Employee }) {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: EMPLOYEE_ITEM_TYPE,
    item: { employeeId: employee.id } as EmployeeDragItem,
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  }), [employee.id]);

  return (
    <div
      ref={drag}
      className={`p-3 rounded-lg border-2 cursor-move hover:shadow-md transition-all ${
        isDragging ? 'opacity-50' : ''
      }`}
      style={{
        backgroundColor: employee.color + '15',
        borderColor: employee.color + '40'
      }}
    >
      <div className="flex items-center gap-2">
        <div
          className="w-3 h-3 rounded-full flex-shrink-0"
          style={{ backgroundColor: employee.color }}
        />
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm truncate" style={{ color: employee.color }}>
            {employee.name}
          </div>
          <div className="text-xs text-gray-500 truncate">
            {employee.roles.length > 0 ? `${employee.roles.length} Rolle(n)` : 'Keine Rollen'}
          </div>
        </div>
      </div>
    </div>
  );
}

interface DayColumnProps {
  date: Date;
  weekType: WeekType;
  shifts: Shift[];
  onDrop: (shift: Shift, newDate: string) => void;
  onEmployeeDrop: (employeeId: string, date: string, weekType: WeekType) => void;
  onClick: (date: Date) => void;
  onEdit: (shift: Shift) => void;
  onDelete: (shift: Shift) => void;
}

function DayColumn({
  date, weekType, shifts, onDrop, onEmployeeDrop, onClick, onEdit, onDelete
}: DayColumnProps) {
  const dateStr = date.toISOString().split('T')[0];
  const dayShifts = shifts.filter(s => s.date === dateStr && s.week === weekType);
  const lanes = useMemo(() => assignLanes(dayShifts), [dayShifts]);

  const onDropRef = useRef(onDrop);
  onDropRef.current = onDrop;
  const onEmployeeDropRef = useRef(onEmployeeDrop);
  onEmployeeDropRef.current = onEmployeeDrop;
  const onClickRef = useRef(onClick);
  onClickRef.current = onClick;

  const [{ isOver }, drop] = useDrop(() => ({
    accept: [ITEM_TYPE, EMPLOYEE_ITEM_TYPE],
    drop: (item: DragItem | EmployeeDragItem) => {
      if ('shift' in item) {
        if (item.fromDate !== dateStr) {
          onDropRef.current(item.shift, dateStr);
        }
      } else if ('employeeId' in item) {
        onEmployeeDropRef.current(item.employeeId, dateStr, weekType);
      }
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
    }),
  }), [dateStr, weekType]);

  const isToday = date.toDateString() === new Date().toDateString();

  return (
    <div className="flex-1 min-w-[100px] flex flex-col" role="gridcell" aria-label={date.toLocaleDateString('de-DE', { timeZone: TIMEZONE, weekday: 'long', day: 'numeric', month: 'long' })}>
      <div
        className={`sticky top-0 z-20 text-center py-2 text-sm font-medium border-b ${
          isToday ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-700'
        }`}
      >
        {date.toLocaleDateString('de-DE', { timeZone: TIMEZONE, weekday: 'short' })}
        <br />
        <span className="text-xs">{date.toLocaleDateString('de-DE', { timeZone: TIMEZONE, day: 'numeric', month: '2-digit' })}</span>
      </div>
      <div
        ref={drop}
        onClick={() => onClick(date)}
        className={`relative flex-1 cursor-pointer transition-colors ${
          isOver ? 'bg-blue-50' : ''
        } ${isToday ? 'bg-blue-50/30' : ''}`}
        style={{ minHeight: `${HOURS.length * HOUR_HEIGHT}px` }}
      >
        {HOURS.map(hour => (
          <div
            key={hour}
            className="border-b border-gray-100"
            style={{ height: `${HOUR_HEIGHT}px` }}
          />
        ))}
        {lanes.map(({ shift, lane, totalLanes }) => (
          <ShiftBar
            key={shift.id}
            shift={shift}
            lane={lane}
            totalLanes={totalLanes}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        ))}
      </div>
    </div>
  );
}

function EditShiftDialog({
  shift,
  open,
  onClose,
  onSave
}: {
  shift: Shift | null;
  open: boolean;
  onClose: () => void;
  onSave: (shift: Shift) => void;
}) {
  const { employees } = useApp();
  const [formData, setFormData] = useState<Shift>(
    shift || {
      id: '',
      employeeId: '',
      date: '',
      week: 'A',
      startTime: '08:00',
      endTime: '18:00',
      breakStart: '12:00',
      breakEnd: '13:00',
    }
  );

  React.useEffect(() => {
    if (shift) {
      setFormData(shift);
    }
  }, [shift]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Schicht bearbeiten</DialogTitle>
          <DialogDescription>
            Ändern Sie die Schichtdetails und speichern Sie die Änderungen.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="employee">Mitarbeiter</Label>
            <select
              id="employee"
              className="w-full border rounded-md px-3 py-2"
              value={formData.employeeId}
              onChange={(e) => setFormData({ ...formData, employeeId: e.target.value })}
              required
            >
              <option value="">Mitarbeiter auswählen</option>
              {employees.map(emp => (
                <option key={emp.id} value={emp.id}>{emp.name}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="startTime">Startzeit</Label>
              <Input
                id="startTime"
                type="time"
                value={formData.startTime}
                onChange={(e) => setFormData({ ...formData, startTime: e.target.value })}
                required
              />
            </div>
            <div>
              <Label htmlFor="endTime">Endzeit</Label>
              <Input
                id="endTime"
                type="time"
                value={formData.endTime}
                onChange={(e) => setFormData({ ...formData, endTime: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="breakStart">Pause Start</Label>
              <Input
                id="breakStart"
                type="time"
                value={formData.breakStart || ''}
                onChange={(e) => setFormData({ ...formData, breakStart: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="breakEnd">Pause Ende</Label>
              <Input
                id="breakEnd"
                type="time"
                value={formData.breakEnd || ''}
                onChange={(e) => setFormData({ ...formData, breakEnd: e.target.value })}
              />
            </div>
          </div>

          <div>
            <Label>Woche</Label>
            <div className="flex gap-2 mt-1">
              <Button
                type="button"
                size="sm"
                variant={formData.week === 'A' ? 'default' : 'outline'}
                className={formData.week === 'A' ? 'bg-blue-500' : ''}
                onClick={() => setFormData({ ...formData, week: 'A' })}
              >
                A
              </Button>
              <Button
                type="button"
                size="sm"
                variant={formData.week === 'B' ? 'default' : 'outline'}
                className={formData.week === 'B' ? 'bg-purple-500' : ''}
                onClick={() => setFormData({ ...formData, week: 'B' })}
              >
                B
              </Button>
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Abbrechen
            </Button>
            <Button type="submit">
              Speichern
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function AddShiftDialog({
  date,
  week,
  open,
  onClose,
  onSave
}: {
  date: Date | null;
  week: WeekType;
  open: boolean;
  onClose: () => void;
  onSave: (shift: Shift) => void;
}) {
  const { employees } = useApp();
  const [formData, setFormData] = useState<Shift>({
    id: Date.now().toString(),
    employeeId: '',
    date: date?.toISOString().split('T')[0] || '',
    week: week,
    startTime: '08:00',
    endTime: '18:00',
    breakStart: '12:00',
    breakEnd: '13:00',
  });

  React.useEffect(() => {
    if (date) {
      setFormData(prev => ({
        ...prev,
        date: date.toISOString().split('T')[0],
        week: week,
      }));
    }
  }, [date, week]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.employeeId) {
      toast.error('Bitte wählen Sie einen Mitarbeiter');
      return;
    }
    onSave({ ...formData, id: Date.now().toString() });
    onClose();
    setFormData({
      id: Date.now().toString(),
      employeeId: '',
      date: date?.toISOString().split('T')[0] || '',
      week: week,
      startTime: '08:00',
      endTime: '18:00',
      breakStart: '12:00',
      breakEnd: '13:00',
    });
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            Schicht hinzufügen - {date?.toLocaleDateString('de-DE', { timeZone: TIMEZONE })}
          </DialogTitle>
          <DialogDescription>
            Fügen Sie eine neue Schicht für den ausgewählten Tag hinzu.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="employee">Mitarbeiter</Label>
            <select
              id="employee"
              className="w-full border rounded-md px-3 py-2"
              value={formData.employeeId}
              onChange={(e) => setFormData({ ...formData, employeeId: e.target.value })}
              required
            >
              <option value="">Mitarbeiter auswählen</option>
              {employees.map(emp => (
                <option key={emp.id} value={emp.id}>{emp.name}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="startTime">Startzeit</Label>
              <Input
                id="startTime"
                type="time"
                value={formData.startTime}
                onChange={(e) => setFormData({ ...formData, startTime: e.target.value })}
                required
              />
            </div>
            <div>
              <Label htmlFor="endTime">Endzeit</Label>
              <Input
                id="endTime"
                type="time"
                value={formData.endTime}
                onChange={(e) => setFormData({ ...formData, endTime: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="breakStart">Pause Start</Label>
              <Input
                id="breakStart"
                type="time"
                value={formData.breakStart || ''}
                onChange={(e) => setFormData({ ...formData, breakStart: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="breakEnd">Pause Ende</Label>
              <Input
                id="breakEnd"
                type="time"
                value={formData.breakEnd || ''}
                onChange={(e) => setFormData({ ...formData, breakEnd: e.target.value })}
              />
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Abbrechen
            </Button>
            <Button type="submit">
              Hinzufügen
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function EditableScheduleCalendar({
  schedule,
  currentWeek,
  onUpdateSchedule,
  onSaveShifts
}: EditableScheduleCalendarProps) {
  const { employees } = useApp();
  const [editingShift, setEditingShift] = useState<Shift | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [showSaturday, setShowSaturday] = useState(true);
  const [showSunday, setShowSunday] = useState(true);
  const [showEmployeePanel, setShowEmployeePanel] = useState(true);
  const [saving, setSaving] = useState(false);
  const isMobile = useMediaQuery('(max-width: 768px)');

  const handleDrop = (shift: Shift, newDate: string) => {
    const updatedShifts = schedule.shifts.map(s =>
      s.id === shift.id ? { ...s, date: newDate } : s
    );
    onUpdateSchedule({ ...schedule, shifts: updatedShifts });
    toast.success('Schicht verschoben');
  };

  const handleEmployeeDrop = (employeeId: string, date: string, weekType: WeekType) => {
    const employee = employees.find(e => e.id === employeeId);
    if (!employee) return;

    const dateObj = new Date(date);
    const dayIndex = dateObj.getDay();
    const daysMap = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
    const dayOfWeek = daysMap[dayIndex] as keyof typeof employee['workingHours']['weekA'];
    const weekKey = weekType === 'A' ? 'weekA' : 'weekB';
    const workingHours = employee.workingHours[weekKey][dayOfWeek];

    const newShift: Shift = {
      id: `${Date.now()}`,
      employeeId,
      date,
      week: weekType,
      startTime: workingHours.enabled ? workingHours.start : '08:00',
      endTime: workingHours.enabled ? workingHours.end : '18:00',
      breakStart: employee.breakTime.start,
      breakEnd: employee.breakTime.end,
    };

    const updatedShifts = [...schedule.shifts, newShift];
    onUpdateSchedule({ ...schedule, shifts: updatedShifts });
    toast.success(`${employee.name} wurde hinzugefügt`);
  };

  const handleEdit = (shift: Shift) => {
    setEditingShift(shift);
    setEditDialogOpen(true);
  };

  const handleSaveEdit = (updatedShift: Shift) => {
    const updatedShifts = schedule.shifts.map(s =>
      s.id === updatedShift.id ? updatedShift : s
    );
    onUpdateSchedule({ ...schedule, shifts: updatedShifts });
    toast.success('Schicht aktualisiert');
  };

  const handleDelete = (shift: Shift) => {
    if (confirm('Möchten Sie diese Schicht wirklich löschen?')) {
      const updatedShifts = schedule.shifts.filter(s => s.id !== shift.id);
      onUpdateSchedule({ ...schedule, shifts: updatedShifts });
      toast.success('Schicht gelöscht');
    }
  };

  const handleDayClick = (date: Date) => {
    setSelectedDate(date);
    setAddDialogOpen(true);
  };

  const handleAddShift = (newShift: Shift) => {
    const updatedShifts = [...schedule.shifts, newShift];
    onUpdateSchedule({ ...schedule, shifts: updatedShifts });
    toast.success('Schicht hinzugefügt');
  };

  const handleSave = async () => {
    if (!onSaveShifts) return;
    setSaving(true);
    try {
      await onSaveShifts(schedule.shifts);
      toast.success('Alle Schichten gespeichert');
    } catch {
      toast.error('Fehler beim Speichern der Schichten');
    } finally {
      setSaving(false);
    }
  };

  const startDate = new Date(schedule.startDate);
  const endDate = new Date(schedule.endDate);
  const days: Date[] = [];
  let currentDate = new Date(startDate);
  while (currentDate <= endDate) {
    days.push(new Date(currentDate));
    currentDate.setDate(currentDate.getDate() + 1);
  }

  const weeks: Date[][] = [];
  let currentWeekDays: Date[] = [];
  days.forEach((day, index) => {
    if (day.getDay() === 1 && currentWeekDays.length > 0) {
      weeks.push(currentWeekDays);
      currentWeekDays = [];
    }
    currentWeekDays.push(day);
    if (index === days.length - 1) {
      weeks.push(currentWeekDays);
    }
  });

  const weekLabel = currentWeek === 'A' ? 'Woche A' : 'Woche B';

  return (
    <DndProvider backend={TouchBackend} options={{ enableMouseEvents: true }}>
      {isMobile ? (
        <ShiftListView
          shifts={schedule.shifts.filter(s => s.week === currentWeek)}
          employees={employees}
          weekLabel={weekLabel}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      ) : (
      <div className="space-y-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800">
            💡 <strong>Tipp:</strong> Ziehen Sie Schichten per Drag & Drop, um sie zu verschieben.
            Klicken Sie auf einen Tag, um eine neue Schicht hinzuzufügen, oder ziehen Sie Mitarbeiter aus dem Mitarbeiterpool auf einen Tag.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowEmployeePanel(!showEmployeePanel)}
          >
            <Users className="h-4 w-4 mr-2" />
            {showEmployeePanel ? 'Mitarbeiterpool ausblenden' : 'Mitarbeiterpool anzeigen'}
          </Button>
          {onSaveShifts && (
            <Button
              variant="default"
              size="sm"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Speichern...</>
              ) : (
                <><Save className="h-4 w-4 mr-2" />Speichern</>
              )}
            </Button>
          )}
        </div>

        {showEmployeePanel && (
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <Users className="h-5 w-5 text-blue-600" />
              <h3 className="font-medium">Mitarbeiterpool</h3>
              <span className="text-sm text-gray-500">({employees.length} Mitarbeiter)</span>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Ziehen Sie Mitarbeiter per Drag & Drop auf einen Tag, um sie hinzuzufügen.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 max-h-60 overflow-y-auto">
              {employees.map(employee => (
                <EmployeeCard key={employee.id} employee={employee} />
              ))}
            </div>
          </div>
        )}

        <div className="flex gap-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="flex items-center gap-2">
            <Checkbox
              id="show-saturday"
              checked={showSaturday}
              onCheckedChange={(checked) => setShowSaturday(checked as boolean)}
            />
            <Label
              htmlFor="show-saturday"
              className="text-sm font-normal cursor-pointer"
            >
              Samstag anzeigen
            </Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="show-sunday"
              checked={showSunday}
              onCheckedChange={(checked) => setShowSunday(checked as boolean)}
            />
            <Label
              htmlFor="show-sunday"
              className="text-sm font-normal cursor-pointer"
            >
              Sonntag anzeigen
            </Label>
          </div>
        </div>

        <div className="border rounded-lg overflow-x-auto">
          {weeks.map((week, weekIndex) => {
            const weekType = getWeekType(week[0]);

            if (weekType !== currentWeek) return null;

            const visibleDays = week.filter(day => {
              const d = day.getDay();
              if (d === 6 && !showSaturday) return false;
              if (d === 0 && !showSunday) return false;
              return true;
            });

            if (visibleDays.length === 0) return null;

            return (
              <div key={weekIndex} className="min-w-[600px]">
                <div className="flex">
                  <div
                    className="sticky left-0 z-10 bg-white border-r flex-shrink-0"
                    style={{ width: '52px' }}
                  >
                    <div className="h-[53px] border-b bg-gray-100" />
                    {HOURS.map(hour => (
                      <div
                        key={hour}
                        className="flex items-start justify-center text-[10px] text-gray-400 leading-none pt-0.5 border-b border-gray-100"
                        style={{ height: `${HOUR_HEIGHT}px` }}
                      >
                        {`${String(hour).padStart(2, '0')}:00`}
                      </div>
                    ))}
                  </div>
                  {visibleDays.map(day => (
                    <DayColumn
                      key={day.toISOString()}
                      date={day}
                      weekType={weekType}
                      shifts={schedule.shifts}
                      onDrop={handleDrop}
                      onEmployeeDrop={handleEmployeeDrop}
                      onClick={handleDayClick}
                      onEdit={handleEdit}
                      onDelete={handleDelete}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      )}

      <EditShiftDialog
        shift={editingShift}
        open={editDialogOpen}
        onClose={() => {
          setEditDialogOpen(false);
          setEditingShift(null);
        }}
        onSave={handleSaveEdit}
      />

      <AddShiftDialog
        date={selectedDate}
        week={currentWeek}
        open={addDialogOpen}
        onClose={() => {
          setAddDialogOpen(false);
          setSelectedDate(null);
        }}
        onSave={handleAddShift}
      />
    </DndProvider>
  );
}
