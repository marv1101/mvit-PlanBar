import React, { useMemo, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useDrag, useDrop, DndProvider } from 'react-dnd';
import { TouchBackend } from 'react-dnd-touch-backend';
import { useApp } from '../context/AppContext';
import { Shift, Schedule, WeekType, Request } from '../../types';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from './ui/alert-dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Button } from './ui/button';
import { Checkbox } from './ui/checkbox';
import { getWeekType } from '../lib/week';
import { useMediaQuery } from '../lib/useMediaQuery';
import { TIMEZONE } from '../lib/timezone';
import { sanitizeLabel } from '../lib/sanitize';
import { ShiftListView } from './ShiftListView';
import { SwimlaneCalendar } from './SwimlaneCalendar';
import { Pencil, Trash2, Users, Save, Loader2, LayoutGrid, CalendarDays } from 'lucide-react';
import { toast } from 'sonner';
import type { Employee } from '../../types';
import {
  ITEM_TYPE, EMPLOYEE_ITEM_TYPE, BREAK_START_ITEM_TYPE, BREAK_END_ITEM_TYPE,
  START_HOUR, END_HOUR, SNAP_MINUTES_SHIFT, SNAP_MINUTES_BREAK,
  HOURS, toMinutes, formatTime, snapMinutes,
} from './schedule/shared/CalendarUtils';
import type { DragItem, EmployeeDragItem, BreakDragItem } from './schedule/shared/CalendarUtils';
import { EmployeeCard, BreakStartHandle, BreakEndHandle } from './schedule/shared/CalendarComponents';
import { WishOverlay } from './WishOverlay';
import { useApprovedWishes } from '../hooks/useShiftWishes';
import { assignLanes, getShiftStyle, getBreakStyle, HOUR_HEIGHT } from './schedule/calendarLayout';

export type ShiftHoverInfo = {
  type: 'shift' | 'inDayShift';
  minutes: number;
  duration: number;
  color: string;
};

export type BreakHoverInfo = {
  type: 'break';
  minutes: number;
  shiftId: string;
  breakType: 'start' | 'end';
  color: string;
};

export type HoverInfo = ShiftHoverInfo | BreakHoverInfo;

interface EditableScheduleCalendarProps {
  schedule: Schedule;
  currentWeek: WeekType;
  onUpdateSchedule: (schedule: Schedule) => void;
  onSaveShifts?: (shifts: Shift[]) => Promise<void>;
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
  const breakStyle = getBreakStyle(shift);

  return (
    <motion.div
      ref={drag}
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{
        opacity: isDragging ? 0.25 : 1,
        scale: isDragging ? 0.95 : 1,
        boxShadow: isDragging
          ? '0 0 0 2px rgba(59,130,246,0.3)'
          : '0 1px 2px rgba(0,0,0,0.05)',
      }}
      exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.15 } }}
      transition={{ type: 'spring', stiffness: 400, damping: 30, mass: 0.8 }}
      whileHover={{ scale: 1.02, y: -1 }}
      whileTap={{ scale: 0.98 }}
      className="absolute rounded overflow-hidden cursor-move group z-10"
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
      <div className="flex flex-col justify-center h-full px-1.5 py-0.5 text-[11px] leading-tight min-w-0">
        {shift.label && (
          <span className="font-semibold truncate text-gray-800 leading-tight">
            {shift.label}
          </span>
        )}
        <span className="font-medium truncate flex items-center gap-1" style={{ color: employee.color }}>
          <span className={`inline-flex items-center justify-center w-3.5 h-3.5 rounded text-[9px] font-bold leading-none flex-shrink-0 ${
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

      {breakStyle && (
        <div
          className="absolute left-0 right-0 pointer-events-none"
          style={{
            top: `${breakStyle.top}px`,
            height: `${breakStyle.height}px`,
            borderTop: '2px solid rgba(0,0,0,0.15)',
            borderBottom: '2px solid rgba(0,0,0,0.15)',
          }}
        />
      )}

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
    </motion.div>
  );
}



interface DayColumnProps {
  date: Date;
  weekType: WeekType;
  shifts: Shift[];
  approvedWishes: Request[];
  employees: Employee[];
  onDrop: (shift: Shift, newDate: string) => void;
  onDropInDay: (shift: Shift, newStartTime: string, newEndTime: string) => void;
  onEmployeeDrop: (employeeId: string, date: string, weekType: WeekType) => void;
  onBreakUpdate: (shiftId: string, updatedShift: Shift) => void;
  onClick: (date: Date) => void;
  onEdit: (shift: Shift) => void;
  onDelete: (shift: Shift) => void;
  onWishClick?: (wish: Request) => void;
}

function DayColumn({
  date, weekType, shifts, approvedWishes, employees, onDrop, onDropInDay, onEmployeeDrop, onBreakUpdate, onClick, onEdit, onDelete, onWishClick
}: DayColumnProps) {
  const dateStr = date.toISOString().split('T')[0];
  const dayShifts = shifts.filter(s => s.date === dateStr);
  const lanes = useMemo(() => assignLanes(dayShifts), [dayShifts]);

  const [hoverInfo, setHoverInfo] = useState<HoverInfo | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const employeesRef = useRef(employees);
  employeesRef.current = employees;

  const onDropRef = useRef(onDrop);
  onDropRef.current = onDrop;
  const onDropInDayRef = useRef(onDropInDay);
  onDropInDayRef.current = onDropInDay;
  const onEmployeeDropRef = useRef(onEmployeeDrop);
  onEmployeeDropRef.current = onEmployeeDrop;
  const onBreakUpdateRef = useRef(onBreakUpdate);
  onBreakUpdateRef.current = onBreakUpdate;
  const onClickRef = useRef(onClick);
  onClickRef.current = onClick;


  const [{ isOver }, drop] = useDrop(() => ({
    accept: [ITEM_TYPE, EMPLOYEE_ITEM_TYPE, BREAK_START_ITEM_TYPE, BREAK_END_ITEM_TYPE],
    hover: (item: DragItem | EmployeeDragItem | BreakDragItem, monitor) => {
      const offset = monitor.getClientOffset();
      if (!offset || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const y = offset.y - rect.top;
      const fromTopMinutes = (y / HOUR_HEIGHT) * 60;

      if ('breakType' in item) {
        const snapped = snapMinutes(fromTopMinutes, SNAP_MINUTES_BREAK);
        const clamped = Math.max(START_HOUR * 60, Math.min(snapped, END_HOUR * 60));
        const emp = employeesRef.current.find(e => e.id === item.shift.employeeId);
        setHoverInfo({
          type: 'break',
          minutes: clamped,
          shiftId: item.shift.id,
          breakType: item.breakType,
          color: emp?.color || '#3b82f6',
        });
        return;
      }

      if ('shift' in item) {
        const snapped = snapMinutes(fromTopMinutes, SNAP_MINUTES_SHIFT);
        const clamped = Math.max(0, Math.min(snapped, (END_HOUR - START_HOUR) * 60));
        const dur = toMinutes(item.shift.endTime) - toMinutes(item.shift.startTime);
        const maxTop = (END_HOUR - START_HOUR) * 60 - dur;
        const positionClamped = Math.max(0, Math.min(clamped, maxTop));

        if (item.fromDate === dateStr) {
          setHoverInfo({
            type: 'inDayShift',
            minutes: positionClamped,
            duration: dur,
            color: employeesRef.current.find(e => e.id === item.shift.employeeId)?.color || '#3b82f6',
          });
        } else {
          setHoverInfo({
            type: 'shift',
            minutes: positionClamped,
            duration: dur,
            color: employeesRef.current.find(e => e.id === item.shift.employeeId)?.color || '#3b82f6',
          });
        }
        return;
      }

      if ('employeeId' in item) {
        const snapped = snapMinutes(fromTopMinutes, SNAP_MINUTES_SHIFT);
        const dur = 480;
        const maxTop = (END_HOUR - START_HOUR) * 60 - dur;
        const clamped = Math.max(0, Math.min(snapped, maxTop));
        const emp = employeesRef.current.find(e => e.id === item.employeeId);
        setHoverInfo({ type: 'shift', minutes: clamped, duration: dur, color: emp?.color || '#3b82f6' });
      }
    },
    drop: (item: DragItem | EmployeeDragItem | BreakDragItem, monitor) => {
      setHoverInfo(null);

      if ('breakType' in item) {
        const offset = monitor.getClientOffset();
        if (!offset || !containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();
        const y = offset.y - rect.top;
        const fromTopMinutes = (y / HOUR_HEIGHT) * 60;
        const snapped = snapMinutes(fromTopMinutes, SNAP_MINUTES_BREAK);
        const clamped = Math.max(START_HOUR * 60, Math.min(snapped, END_HOUR * 60));
        const newTime = formatTime(clamped);
        const shift = item.shift;
        const updated = { ...shift };

        if (item.breakType === 'start') {
          if (toMinutes(newTime) <= toMinutes(shift.startTime)) return;
          if (shift.breakEnd && toMinutes(newTime) >= toMinutes(shift.breakEnd)) return;
          updated.breakStart = newTime;
        } else {
          if (shift.breakStart && toMinutes(newTime) <= toMinutes(shift.breakStart)) return;
          if (toMinutes(newTime) >= toMinutes(shift.endTime)) return;
          updated.breakEnd = newTime;
        }

        onBreakUpdateRef.current(shift.id, updated);
        toast.success(`Pause ${item.breakType === 'start' ? 'Start' : 'Ende'} auf ${newTime} geändert`);
        return;
      }

      if ('shift' in item) {
        if (item.fromDate === dateStr) {
          const offset = monitor.getClientOffset();
          if (!offset || !containerRef.current) return;
          const rect = containerRef.current.getBoundingClientRect();
          const y = offset.y - rect.top;
          const fromTopMinutes = (y / HOUR_HEIGHT) * 60;
          const snapped = snapMinutes(fromTopMinutes, SNAP_MINUTES_SHIFT);
          const clamped = Math.max(0, Math.min(snapped, (END_HOUR - START_HOUR) * 60));
          const newStartMinutes = clamped + START_HOUR * 60;
          const dur = toMinutes(item.shift.endTime) - toMinutes(item.shift.startTime);
          const newStart = formatTime(newStartMinutes);
          const newEnd = formatTime(newStartMinutes + dur);
          onDropInDayRef.current(item.shift, newStart, newEnd);
        } else {
          onDropRef.current(item.shift, dateStr);
        }
        return;
      }

      if ('employeeId' in item) {
        onEmployeeDropRef.current(item.employeeId, dateStr, weekType);
      }
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
    }),
  }), [dateStr, weekType]);

  React.useEffect(() => {
    if (!isOver) setHoverInfo(null);
  }, [isOver]);

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
      <motion.div
        ref={(node: HTMLDivElement | null) => {
          containerRef.current = node;
          drop(node);
        }}
        onClick={() => onClick(date)}
        animate={{
          backgroundColor: isToday
            ? 'rgba(59,130,246,0.03)'
            : 'transparent',
        }}
        transition={{ duration: 0.2 }}
        className="relative flex-1 cursor-pointer"
        style={{ minHeight: `${HOURS.length * HOUR_HEIGHT}px` }}
      >
        {HOURS.map(hour => (
          <div
            key={hour}
            className="border-b border-gray-100"
            style={{ height: `${HOUR_HEIGHT}px` }}
          />
        ))}
        {hoverInfo && isOver && hoverInfo.type !== 'break' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.12 }}
            className="absolute left-1 right-1 rounded pointer-events-none z-20"
            style={{
              top: `${(hoverInfo.minutes / 60) * HOUR_HEIGHT}px`,
              height: `${Math.max((hoverInfo.duration / 60) * HOUR_HEIGHT, 24)}px`,
              backgroundColor: hoverInfo.color + '18',
              borderTop: `2px solid ${hoverInfo.color}50`,
              borderBottom: `2px solid ${hoverInfo.color}50`,
              boxShadow: `0 0 0 1px ${hoverInfo.color}20 inset`,
            }}
          />
        )}
        {hoverInfo && isOver && hoverInfo.type === 'break' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.1 }}
            className="absolute left-0 right-0 pointer-events-none z-30"
            style={{
              top: `${((hoverInfo.minutes - START_HOUR * 60) / 60) * HOUR_HEIGHT}px`,
              height: '2px',
              backgroundColor: hoverInfo.color,
              boxShadow: `0 0 6px ${hoverInfo.color}80`,
            }}
          >
            <span className="absolute -top-4 left-1 text-[10px] font-medium px-1 rounded whitespace-nowrap"
              style={{ backgroundColor: hoverInfo.color + '20', color: hoverInfo.color }}>
              {formatTime(hoverInfo.minutes)}
            </span>
          </motion.div>
        )}

        {/* Render approved wishes as overlays */}
        {approvedWishes
          .filter(wish => wish.date === dateStr)
          .map(wish => (
            <WishOverlay
              key={wish.id}
              wish={wish}
              employee={employees.find(e => e.id === wish.employeeId)}
              onClick={onWishClick}
            />
          ))}

        <AnimatePresence mode="popLayout">
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
        </AnimatePresence>
      </motion.div>
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

          <div>
            <Label htmlFor="edit-label">Bezeichnung</Label>
            <Input
              id="edit-label"
              type="text"
              maxLength={100}
              placeholder="z.B. Backoffice, Kasse, Fahrt"
              value={formData.label || ''}
              onChange={(e) => setFormData({ ...formData, label: sanitizeLabel(e.target.value) })}
            />
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

          <div>
            <Label htmlFor="add-label">Bezeichnung</Label>
            <Input
              id="add-label"
              type="text"
              maxLength={100}
              placeholder="z.B. Backoffice, Kasse, Fahrt"
              value={formData.label || ''}
              onChange={(e) => setFormData({ ...formData, label: sanitizeLabel(e.target.value) })}
            />
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
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [shiftToDelete, setShiftToDelete] = useState<Shift | null>(null);
  const [showSaturday, setShowSaturday] = useState(true);
  const [showSunday, setShowSunday] = useState(true);
  const [showEmployeePanel, setShowEmployeePanel] = useState(true);
  const [saving, setSaving] = useState(false);
  const [viewMode, setViewMode] = useState<'timeline' | 'swimlane'>('swimlane');
  const isMobile = useMediaQuery('(max-width: 768px)');

  // Fetch approved wishes for the current schedule
  const { data: approvedWishes = [] } = useApprovedWishes(schedule.id ? Number(schedule.id) : null);

  const handleDrop = (shift: Shift, newDate: string) => {
    const newWeekType = getWeekType(new Date(newDate));
    const updatedShifts = schedule.shifts.map(s =>
      s.id === shift.id ? { ...s, date: newDate, week: newWeekType } : s
    );
    onUpdateSchedule({ ...schedule, shifts: updatedShifts });
    toast.success('Schicht verschoben');
  };

  const handleDropInDay = (shift: Shift, newStartTime: string, newEndTime: string) => {
    const startDiff = toMinutes(newStartTime) - toMinutes(shift.startTime);
    const updatedShifts = schedule.shifts.map(s => {
      if (s.id !== shift.id) return s;
      const updated = { ...s, startTime: newStartTime, endTime: newEndTime };
      if (s.breakStart) {
        updated.breakStart = formatTime(toMinutes(s.breakStart) + startDiff);
      }
      if (s.breakEnd) {
        updated.breakEnd = formatTime(toMinutes(s.breakEnd) + startDiff);
      }
      return updated;
    });
    onUpdateSchedule({ ...schedule, shifts: updatedShifts });
    toast.success('Schicht verschoben');
  };

  const handleBreakUpdate = (shiftId: string, updatedShift: Shift) => {
    const updatedShifts = schedule.shifts.map(s =>
      s.id === shiftId ? updatedShift : s
    );
    onUpdateSchedule({ ...schedule, shifts: updatedShifts });
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
    setShiftToDelete(shift);
    setDeleteDialogOpen(true);
  };

  const confirmDeleteShift = () => {
    if (!shiftToDelete) return;
    const updatedShifts = schedule.shifts.filter(s => s.id !== shiftToDelete.id);
    onUpdateSchedule({ ...schedule, shifts: updatedShifts });
    toast.success('Schicht gelöscht');
    setShiftToDelete(null);
    setDeleteDialogOpen(false);
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
    const utcDate = new Date(Date.UTC(currentDate.getFullYear(), currentDate.getMonth(), currentDate.getDate()));
    days.push(utcDate);
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
      <div className="space-y-4 select-none">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800">
            💡 <strong>Tipp:</strong> Ziehen Sie Schichten per Drag & Drop, um sie zu verschieben.
            Klicken Sie auf einen Tag, um eine neue Schicht hinzuzufügen, oder ziehen Sie Mitarbeiter aus dem Mitarbeiterpool auf einen Tag.
            {viewMode === 'swimlane' && ' In der Mitarbeiter-Ansicht können Sie Pausen per Drag anpassen und Schichten zwischen Mitarbeitern verschieben.'}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowEmployeePanel(!showEmployeePanel)}
          >
            <Users className="h-4 w-4 mr-2" />
            {showEmployeePanel ? 'Mitarbeiterpool ausblenden' : 'Mitarbeiterpool anzeigen'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setViewMode(viewMode === 'timeline' ? 'swimlane' : 'timeline')}
          >
            {viewMode === 'timeline' ? (
              <><LayoutGrid className="h-4 w-4 mr-2" />Mitarbeiter-Ansicht</>
            ) : (
              <><CalendarDays className="h-4 w-4 mr-2" />Timeline-Ansicht</>
            )}
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

        {viewMode === 'timeline' ? (
          <div className="border rounded-lg overflow-x-auto">
            {weeks.map((week, weekIndex) => {
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
                        weekType={currentWeek}
                        shifts={schedule.shifts.filter((s: Shift) => s.week === currentWeek)}
                        approvedWishes={approvedWishes}
                        employees={employees}
                        onDrop={handleDrop}
                        onDropInDay={handleDropInDay}
                        onEmployeeDrop={handleEmployeeDrop}
                        onBreakUpdate={handleBreakUpdate}
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
        ) : (
          <SwimlaneCalendar
            schedule={schedule}
            currentWeek={currentWeek}
            onUpdateSchedule={onUpdateSchedule}
          />
        )}
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
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Schicht löschen</AlertDialogTitle>
            <AlertDialogDescription>
              Möchten Sie diese Schicht wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Abbrechen</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDeleteShift} className="bg-red-600 text-white hover:bg-red-700">
              Löschen
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </DndProvider>
  );
}
