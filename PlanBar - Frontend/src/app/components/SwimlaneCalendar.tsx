import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useDrag, useDrop } from 'react-dnd';
import { useApp } from '../context/AppContext';
import { Shift, Schedule, WeekType, Request } from '../types';
import { Button } from './ui/button';
import { getWeekType } from '../lib/week';
import { TIMEZONE } from '../lib/timezone';
import { sanitizeLabel } from '../lib/sanitize';
import { Pencil, Trash2, Coffee, Maximize2 } from 'lucide-react';
import { toast } from 'sonner';
import type { Employee } from '../types';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from './ui/alert-dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';
import {
  ITEM_TYPE, EMPLOYEE_ITEM_TYPE, BREAK_START_ITEM_TYPE, BREAK_END_ITEM_TYPE,
  START_HOUR, END_HOUR, SNAP_MINUTES_SHIFT, SNAP_MINUTES_BREAK,
  HOURS, toMinutes, formatTime, snapMinutes,
} from './schedule/shared/CalendarUtils';
import type { DragItem, EmployeeDragItem, BreakDragItem } from './schedule/shared/CalendarUtils';
import { BreakStartHandle, BreakEndHandle } from './schedule/shared/CalendarComponents';
import { Tooltip, TooltipContent, TooltipTrigger } from './ui/tooltip';
import { useApprovedWishes } from '../hooks/useShiftWishes';
import { DayDetailDialog } from './schedule/day-popout/DayDetailDialog';
import { useMeasuredSize } from './schedule/day-popout/useMeasuredSize';
import { computePopoutSizes, barTextClass } from './schedule/day-popout/popoutSizes';

const HOUR_WIDTH = 64;
const EMPLOYEE_ROW_HEIGHT = 44;
const WISH_COLORS: Record<string, string> = {
  'urlaubswunsch': '#3b82f6',
  'bevorzugt': '#22c55e',
  'nicht-verfügbar': '#ef4444',
};
const WISH_LABELS: Record<string, string> = {
  'urlaubswunsch': 'Urlaub',
  'bevorzugt': 'Bevorzugt',
  'nicht-verfügbar': 'Nicht verfügbar',
};
function getBreakStyleHorizontal(shift: Shift, hourWidth: number) {
  if (!shift.breakStart || !shift.breakEnd) return null;
  const shiftStart = toMinutes(shift.startTime);
  const breakStart = toMinutes(shift.breakStart);
  const breakEnd = toMinutes(shift.breakEnd);
  if (breakStart <= shiftStart || breakEnd <= breakStart || breakEnd > toMinutes(shift.endTime)) return null;
  const left = ((breakStart - shiftStart) / 60) * hourWidth;
  const width = Math.max(((breakEnd - breakStart) / 60) * hourWidth, 16);
  return { left, width };
}
type HoverInfo = {
  type: 'shift';
  minutes: number;
  duration: number;
  color: string;
  top: number;
} | {
  type: 'break';
  minutes: number;
  shiftId: string;
  breakType: 'start' | 'end';
  color: string;
};

interface SwimlaneCalendarProps {
  schedule: Schedule;
  currentWeek: WeekType;
  onUpdateSchedule: (schedule: Schedule) => void;
}



function ShiftBar({
  shift,
  onEdit,
  onDelete,
  top = 4,
  hourWidth = HOUR_WIDTH,
  barHeight = 36,
}: {
  shift: Shift;
  onEdit: (shift: Shift) => void;
  onDelete: (shift: Shift) => void;
  top?: number;
  hourWidth?: number;
  barHeight?: number;
}) {
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

  const startMin = toMinutes(shift.startTime);
  const endMin = toMinutes(shift.endTime);
  const left = ((startMin - START_HOUR * 60) / 60) * hourWidth;
  const width = Math.max(((endMin - startMin) / 60) * hourWidth, 20);
  const breakStyle = getBreakStyleHorizontal(shift, hourWidth);

  return (
    <motion.div
      ref={(node: HTMLDivElement | null) => { drag(node); }}
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
        left: `${left}px`,
        width: `${width}px`,
        top: `${top}px`,
        height: `${barHeight}px`,
        position: 'absolute',
        backgroundColor: employee.color + '20',
        borderLeft: `3px solid ${employee.color}`,
      }}
      onClick={(e) => {
        e.stopPropagation();
        onEdit(shift);
      }}
    >
      <div className={`flex flex-col justify-center h-full px-1.5 leading-tight min-w-0 ${barTextClass(barHeight)}`}>
        {shift.label && (
          <span className="font-semibold truncate text-gray-800 leading-tight">
            {shift.label}
          </span>
        )}
        <span className="font-medium truncate flex items-center gap-1" style={{ color: employee.color }}>
          <span className={`inline-flex items-center justify-center w-3 h-3 rounded text-[8px] font-bold leading-none flex-shrink-0 ${
            shift.week === 'A' ? 'bg-blue-500 text-white' : 'bg-purple-500 text-white'
          }`}>
            {shift.week}
          </span>
          <span className="text-gray-500 truncate">
            {shift.startTime}–{shift.endTime}
          </span>
        </span>
      </div>

      {breakStyle && (
        <div
          className="absolute top-0 bottom-0 pointer-events-none"
          style={{
            left: `${breakStyle.left}px`,
            width: `${breakStyle.width}px`,
            backgroundImage: `repeating-linear-gradient(45deg, transparent, transparent 3px, rgba(0,0,0,0.06) 3px, rgba(0,0,0,0.06) 6px)`,
            borderLeft: '2px solid rgba(0,0,0,0.2)',
            borderRight: '2px solid rgba(0,0,0,0.2)',
            backgroundColor: 'rgba(0,0,0,0.05)',
          }}
        >
          {breakStyle.width > 28 && (
            <span className="text-[8px] text-gray-600 font-medium px-0.5 whitespace-nowrap pointer-events-none flex items-center gap-0.5 h-full">
              <Coffee className="h-2 w-2" />
              {shift.breakStart}–{shift.breakEnd}
            </span>
          )}
          <BreakStartHandle shift={shift} />
          <BreakEndHandle shift={shift} />
        </div>
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



interface DayBlockProps {
  date: Date;
  shifts: Shift[];
  employees: Employee[];
  onDrop: (shift: Shift, newDate: string) => void;
  onDropInDay: (shift: Shift, newStartTime: string, newEndTime: string) => void;
  onDropOnEmployee: (shift: Shift, newEmployeeId: string) => void;
  onEmployeeDrop: (employeeId: string, date: string) => void;
  onBreakUpdate: (shiftId: string, updatedShift: Shift) => void;
  onClick: (date: Date) => void;
  onEdit: (shift: Shift) => void;
  onDelete: (shift: Shift) => void;
  approvedWishes: Request[];
  onWishClick: (employeeId: string, date: Date) => void;
  onExpand?: (date: Date) => void;
  hourWidth?: number;
  rowHeight?: number;
  barHeight?: number;
}

function DayBlock({
  date, shifts, employees, onDrop, onDropInDay, onDropOnEmployee,
  onEmployeeDrop, onBreakUpdate, onClick, onEdit, onDelete,
  approvedWishes, onWishClick, onExpand, hourWidth = HOUR_WIDTH, rowHeight = EMPLOYEE_ROW_HEIGHT, barHeight = 36
}: DayBlockProps) {
  const dateStr = date.toISOString().split('T')[0];
  const dayShifts = shifts.filter(s => s.date === dateStr);
  const sortedEmployees = [...employees].sort((a, b) => a.name.localeCompare(b.name));

  const [hoverInfo, setHoverInfo] = useState<HoverInfo | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const employeesRef = useRef(employees);
  employeesRef.current = employees;

  const onDropRef = useRef(onDrop);
  onDropRef.current = onDrop;
  const onDropInDayRef = useRef(onDropInDay);
  onDropInDayRef.current = onDropInDay;
  const onDropOnEmployeeRef = useRef(onDropOnEmployee);
  onDropOnEmployeeRef.current = onDropOnEmployee;
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
      const x = offset.x - rect.left;
      const y = offset.y - rect.top;
      const fromLeftMinutes = (x / hourWidth) * 60;
      const employeeIndex = Math.floor((y - 40) / rowHeight);
      const clampedEmployeeIndex = Math.max(0, Math.min(employeeIndex, sortedEmployees.length - 1));
      const emp = sortedEmployees[clampedEmployeeIndex];
      const empColor = emp?.color || '#3b82f6';

      if ('breakType' in item) {
        const snapped = snapMinutes(fromLeftMinutes + START_HOUR * 60, SNAP_MINUTES_BREAK);
        const clamped = Math.max(START_HOUR * 60, Math.min(snapped, END_HOUR * 60));
        setHoverInfo({
          type: 'break',
          minutes: clamped,
          shiftId: item.shift.id,
          breakType: item.breakType,
          color: empColor,
        });
        return;
      }

      const hoverTop = 40 + clampedEmployeeIndex * rowHeight + 4;

      if ('shift' in item) {
        const snapped = snapMinutes(fromLeftMinutes + START_HOUR * 60, SNAP_MINUTES_SHIFT);
        const clamped = Math.max(START_HOUR * 60, Math.min(snapped, END_HOUR * 60));
        const dur = toMinutes(item.shift.endTime) - toMinutes(item.shift.startTime);
        const maxEnd = Math.min(clamped + dur, END_HOUR * 60);
        const positionClamped = Math.max(START_HOUR * 60, maxEnd - dur);
        setHoverInfo({
          type: 'shift',
          minutes: positionClamped - START_HOUR * 60,
          duration: dur,
          color: employeesRef.current.find(e => e.id === item.shift.employeeId)?.color || '#3b82f6',
          top: hoverTop,
        });
        return;
      }

      if ('employeeId' in item) {
        const dur = 480;
        const clamped = Math.max(0, Math.min(fromLeftMinutes, (END_HOUR - START_HOUR) * 60 - dur));
        const emp = employeesRef.current.find(e => e.id === item.employeeId);
        setHoverInfo({ type: 'shift', minutes: clamped, duration: dur, color: emp?.color || '#3b82f6', top: hoverTop });
      }
    },
    drop: (item: DragItem | EmployeeDragItem | BreakDragItem, monitor) => {
      setHoverInfo(null);
      const offset = monitor.getClientOffset();
      if (!offset || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = offset.x - rect.left;
      const y = offset.y - rect.top;
      const fromLeftMinutes = (x / hourWidth) * 60;
      const employeeIndex = Math.floor((y - 40) / rowHeight);
      const clampedEmployeeIndex = Math.max(0, Math.min(employeeIndex, sortedEmployees.length - 1));
      const targetEmployee = sortedEmployees[clampedEmployeeIndex];

      if ('breakType' in item) {
        const snapped = snapMinutes(fromLeftMinutes + START_HOUR * 60, SNAP_MINUTES_BREAK);
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
        const snapped = snapMinutes(fromLeftMinutes + START_HOUR * 60, SNAP_MINUTES_SHIFT);
        const clamped = Math.max(START_HOUR * 60, Math.min(snapped, END_HOUR * 60));
        const newStartMinutes = clamped;
        const dur = toMinutes(item.shift.endTime) - toMinutes(item.shift.startTime);
        const newStart = formatTime(newStartMinutes);
        const newEnd = formatTime(newStartMinutes + dur);

        if (item.fromDate !== dateStr) {
          onDropRef.current(item.shift, dateStr);
          return;
        }

        if (targetEmployee && targetEmployee.id !== item.shift.employeeId) {
          const updated = { ...item.shift, employeeId: targetEmployee.id, startTime: newStart, endTime: newEnd };
          onDropOnEmployeeRef.current(item.shift, targetEmployee.id);
          return;
        }

        onDropInDayRef.current(item.shift, newStart, newEnd);
        return;
      }

      if ('employeeId' in item) {
        onEmployeeDropRef.current(item.employeeId, dateStr);
      }
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
    }),
  }), [dateStr, sortedEmployees]);

  React.useEffect(() => {
    if (!isOver) setHoverInfo(null);
  }, [isOver]);

  return (
    <div className="group border rounded-lg mb-4 overflow-hidden">
      <div className="bg-gray-50 px-4 py-2 font-medium text-sm border-b flex items-center justify-between">
        <span>
          {date.toLocaleDateString('de-DE', { timeZone: TIMEZONE, weekday: 'long', day: 'numeric', month: 'long' })}
        </span>
        {onExpand && (
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-blue-100 text-blue-600 bg-white/80"
                aria-label="Tag vergrößern"
                onClick={(e) => {
                  e.stopPropagation();
                  onExpand(date);
                }}
              >
                <Maximize2 className="h-4 w-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Tag in der Großansicht öffnen</p>
            </TooltipContent>
          </Tooltip>
        )}
      </div>
      <div className="flex">
        <div className="w-40 border-r flex-shrink-0">
          <div className="h-[40px] border-b bg-gray-100" />
          {sortedEmployees.map(emp => (
            <div
              key={emp.id}
              className="border-b flex items-center px-3 text-sm"
              style={{ borderLeft: `3px solid ${emp.color}`, height: `${rowHeight}px` }}
            >
              <span className="truncate">{emp.name}</span>
            </div>
          ))}
        </div>
        <div className="flex-1 overflow-x-auto relative">
          <div
            ref={(node: HTMLDivElement | null) => {
              containerRef.current = node;
              drop(node);
            }}
            className="relative cursor-pointer"
            style={{ minWidth: `${HOURS.length * hourWidth}px` }}
            onClick={() => onClick(date)}
          >
            <div className="flex h-[40px] border-b bg-gray-50">
              {HOURS.map(hour => (
                <div
                  key={hour}
                  className="flex-shrink-0 text-[10px] text-gray-400 flex items-center justify-center border-r border-gray-100"
                  style={{ width: `${hourWidth}px` }}
                >
                  {`${String(hour).padStart(2, '0')}:00`}
                </div>
              ))}
            </div>
            {sortedEmployees.map((emp, empIndex) => {
              const empWish = approvedWishes.find(w => w.employeeId === emp.id && w.date === dateStr);
              return (
              <div
                key={emp.id}
                className="relative border-b border-gray-100"
                style={{ height: `${rowHeight}px` }}
              >
                {HOURS.map(hour => (
                  <div
                    key={hour}
                    className="absolute top-0 bottom-0 border-r border-gray-100"
                    style={{ left: `${(hour - START_HOUR) * hourWidth}px`, width: `${hourWidth}px` }}
                  />
                ))}
                {empWish && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div
                        className="absolute inset-0 cursor-pointer"
                        style={{
                          backgroundColor: WISH_COLORS[empWish.type] + '20',
                          borderLeft: `3px solid ${WISH_COLORS[empWish.type]}`,
                          zIndex: 5,
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onWishClick(emp.id, date);
                        }}
                      >
                        <div className="flex items-center justify-center h-full pointer-events-none">
                          <span className="text-[10px] font-medium text-gray-700 bg-white/80 px-1.5 py-0.5 rounded shadow-sm pointer-events-auto">
                            {emp.name}: {WISH_LABELS[empWish.type] || empWish.type}
                          </span>
                        </div>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="font-semibold">{emp.name}</p>
                      <p>Typ: {WISH_LABELS[empWish.type] || empWish.type}</p>
                      {empWish.notes && <p>Notiz: {empWish.notes}</p>}
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>
              );
            })}
            {hoverInfo && isOver && hoverInfo.type === 'shift' && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.12 }}
                className="absolute rounded pointer-events-none z-20"
                style={{
                  left: `${(hoverInfo.minutes / 60) * hourWidth}px`,
                  width: `${Math.max((hoverInfo.duration / 60) * hourWidth, 20)}px`,
                  top: `${hoverInfo.top}px`,
                  height: `${barHeight}px`,
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
                className="absolute pointer-events-none z-30"
                style={{
                  left: `${((hoverInfo.minutes - START_HOUR * 60) / 60) * hourWidth}px`,
                  width: '2px',
                  top: '4px',
                  bottom: '4px',
                  backgroundColor: hoverInfo.color,
                  boxShadow: `0 0 6px ${hoverInfo.color}80`,
                }}
              >
                <span className="absolute -top-3 left-1 text-[10px] font-medium px-1 rounded whitespace-nowrap"
                  style={{ backgroundColor: hoverInfo.color + '20', color: hoverInfo.color }}>
                  {formatTime(hoverInfo.minutes)}
                </span>
              </motion.div>
            )}
            <AnimatePresence mode="popLayout">
              {dayShifts.map((shift) => {
                const empIdx = sortedEmployees.findIndex(e => e.id === shift.employeeId);
                const shiftTop = 40 + (empIdx >= 0 ? empIdx : 0) * rowHeight + 4;
                return (
                  <ShiftBar
                    key={shift.id}
                    shift={shift}
                    onEdit={onEdit}
                    onDelete={onDelete}
                    top={shiftTop}
                    hourWidth={hourWidth}
                  />
                );
              })}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}

function EditShiftDialog({
  shift,
  open,
  onClose,
  onSave,
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
            <Label htmlFor="label">Bezeichnung</Label>
            <Input
              id="label"
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
  open,
  onClose,
  onSave,
  prefilledEmployeeId,
}: {
  date: Date | null;
  open: boolean;
  onClose: () => void;
  onSave: (shift: Shift) => void;
  prefilledEmployeeId?: string | null;
}) {
  const { employees } = useApp();
  const [formData, setFormData] = useState<Shift>({
    id: Date.now().toString(),
    employeeId: prefilledEmployeeId || '',
    date: date?.toISOString().split('T')[0] || '',
    week: date ? getWeekType(date) : 'A',
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
        week: getWeekType(date),
        ...(prefilledEmployeeId ? { employeeId: prefilledEmployeeId } : {}),
      }));
    }
  }, [date, prefilledEmployeeId]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.employeeId) {
      toast.error('Bitte wählen Sie einen Mitarbeiter');
      return;
    }
    onSave({ ...formData, id: Date.now().toString(), week: getWeekType(new Date(formData.date)) });
    onClose();
    setFormData({
      id: Date.now().toString(),
      employeeId: prefilledEmployeeId || '',
      date: date?.toISOString().split('T')[0] || '',
      week: date ? getWeekType(date) : 'A',
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

export function SwimlaneCalendar({
  schedule,
  currentWeek,
  onUpdateSchedule,
}: SwimlaneCalendarProps) {
  const { employees } = useApp();
  const { data: approvedWishes = [] } = useApprovedWishes(schedule.id ? Number(schedule.id) : null);
  const [editingShift, setEditingShift] = useState<Shift | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [shiftToDelete, setShiftToDelete] = useState<Shift | null>(null);
  const [wishPrefilledEmployeeId, setWishPrefilledEmployeeId] = useState<string | null>(null);

  const handleWishClick = (employeeId: string, date: Date) => {
    setWishPrefilledEmployeeId(employeeId);
    setSelectedDate(date);
    setAddDialogOpen(true);
  };

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

  const handleDropOnEmployee = (shift: Shift, newEmployeeId: string) => {
    const updatedShifts = schedule.shifts.map(s =>
      s.id === shift.id ? { ...s, employeeId: newEmployeeId } : s
    );
    onUpdateSchedule({ ...schedule, shifts: updatedShifts });
    toast.success('Mitarbeiter geändert');
  };

  const handleBreakUpdate = (shiftId: string, updatedShift: Shift) => {
    const updatedShifts = schedule.shifts.map(s =>
      s.id === shiftId ? updatedShift : s
    );
    onUpdateSchedule({ ...schedule, shifts: updatedShifts });
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

  const handleEmployeeDrop = (employeeId: string, date: string) => {
    const employee = employees.find(e => e.id === employeeId);
    if (!employee) return;

    const dateObj = new Date(date);
    const dayIndex = dateObj.getDay();
    const daysMap = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
    const dayOfWeek = daysMap[dayIndex] as keyof typeof employee['workingHours']['weekA'];
    const weekType = getWeekType(dateObj);
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

  const startDate = new Date(schedule.startDate);
  const endDate = new Date(schedule.endDate);
  const allDays: Date[] = [];
  let currentDate = new Date(startDate);
  while (currentDate <= endDate) {
    allDays.push(new Date(Date.UTC(currentDate.getFullYear(), currentDate.getMonth(), currentDate.getDate())));
    currentDate.setDate(currentDate.getDate() + 1);
  }
  const days = allDays.filter(day => getWeekType(day) === currentWeek);

  const [popoutDate, setPopoutDate] = useState<Date | null>(null);
  const popoutIndex = popoutDate ? days.findIndex(d => d.toISOString() === popoutDate.toISOString()) : -1;

  const popoutContentRef = useRef<HTMLDivElement>(null);
  const popoutSize = useMeasuredSize(popoutContentRef);
  const popoutSizes = computePopoutSizes(popoutSize.width, popoutSize.height, employees.length);

  const handleExpandDay = (date: Date) => setPopoutDate(date);

  return (
    <div className="space-y-4 select-none">
      <div>
        {days.map(day => (
          <DayBlock
            key={day.toISOString()}
            date={day}
            shifts={schedule.shifts}
            employees={employees}
            onDrop={handleDrop}
            onDropInDay={handleDropInDay}
            onDropOnEmployee={handleDropOnEmployee}
            onEmployeeDrop={handleEmployeeDrop}
            onBreakUpdate={handleBreakUpdate}
            onClick={handleDayClick}
            onEdit={handleEdit}
            onDelete={handleDelete}
            approvedWishes={approvedWishes}
            onWishClick={handleWishClick}
            onExpand={handleExpandDay}
          />
        ))}
      </div>

      <DayDetailDialog
        open={popoutDate !== null}
        onOpenChange={(open) => !open && setPopoutDate(null)}
        title={
          popoutDate
            ? popoutDate.toLocaleDateString('de-DE', { timeZone: TIMEZONE, weekday: 'long', day: 'numeric', month: 'numeric', year: 'numeric' })
            : ''
        }
        description="Vergrößerte Tagesansicht – Schichten verschieben, bearbeiten und hinzufügen"
        showNavigation
        fullScreen
        hasPrev={popoutIndex > 0}
        hasNext={popoutIndex >= 0 && popoutIndex < days.length - 1}
        onPrev={() => setPopoutDate(days[popoutIndex - 1] ?? null)}
        onNext={() => setPopoutDate(days[popoutIndex + 1] ?? null)}
      >
        <div ref={popoutContentRef} className="h-full min-h-0">
          {popoutDate && (
            <DayBlock
              date={popoutDate}
              shifts={schedule.shifts}
              employees={employees}
              onDrop={handleDrop}
              onDropInDay={handleDropInDay}
              onDropOnEmployee={handleDropOnEmployee}
              onEmployeeDrop={handleEmployeeDrop}
              onBreakUpdate={handleBreakUpdate}
              onClick={handleDayClick}
              onEdit={handleEdit}
              onDelete={handleDelete}
              approvedWishes={approvedWishes}
              onWishClick={handleWishClick}
              hourWidth={popoutSizes.hourWidth}
              rowHeight={popoutSizes.rowHeight}
              barHeight={popoutSizes.barHeight}
            />
          )}
        </div>
      </DayDetailDialog>

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
        open={addDialogOpen}
        onClose={() => {
          setAddDialogOpen(false);
          setSelectedDate(null);
          setWishPrefilledEmployeeId(null);
        }}
        onSave={handleAddShift}
        prefilledEmployeeId={wishPrefilledEmployeeId}
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
    </div>
  );
}
