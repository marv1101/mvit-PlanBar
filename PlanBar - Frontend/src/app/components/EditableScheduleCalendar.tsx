import React, { useState } from 'react';
import { useDrag, useDrop, DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { useApp } from '../context/AppContext';
import { Shift, Schedule, WeekType } from '../types';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Button } from './ui/button';
import { Checkbox } from './ui/checkbox';
import { Pencil, Trash2, X, Users, Save, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import type { Employee } from '../types';

const ITEM_TYPE = 'SHIFT';
const EMPLOYEE_ITEM_TYPE = 'EMPLOYEE';

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

function ShiftCard({ 
  shift, 
  onEdit, 
  onDelete 
}: { 
  shift: Shift; 
  onEdit: (shift: Shift) => void;
  onDelete: (shift: Shift) => void;
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

  return (
    <div
      ref={drag}
      className={`p-2 rounded text-xs mb-1 cursor-move relative group ${
        isDragging ? 'opacity-50' : ''
      }`}
      style={{ backgroundColor: employee.color + '20', borderLeft: `3px solid ${employee.color}` }}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1 min-w-0">
          <div className="font-medium truncate" style={{ color: employee.color }}>
            {employee.name}
          </div>
          <div className="text-gray-600">
            {shift.startTime} - {shift.endTime}
          </div>
        </div>
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEdit(shift);
            }}
            className="p-1 hover:bg-gray-200 rounded"
          >
            <Pencil className="h-3 w-3" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(shift);
            }}
            className="p-1 hover:bg-red-100 rounded text-red-600"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
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

function DayCell({
  date,
  shifts,
  weekType,
  onDrop,
  onEmployeeDrop,
  onClick,
  onEdit,
  onDelete
}: {
  date: Date;
  shifts: Shift[];
  weekType: WeekType;
  onDrop: (shift: Shift, newDate: string) => void;
  onEmployeeDrop: (employeeId: string, date: string, weekType: WeekType) => void;
  onClick: (date: Date) => void;
  onEdit: (shift: Shift) => void;
  onDelete: (shift: Shift) => void;
}) {
  const dateStr = date.toISOString().split('T')[0];
  const dayShifts = shifts.filter(s => s.date === dateStr && s.week === weekType);

  const [{ isOver, canDrop }, drop] = useDrop(() => ({
    accept: [ITEM_TYPE, EMPLOYEE_ITEM_TYPE],
    drop: (item: DragItem | EmployeeDragItem) => {
      if ('shift' in item) {
        // It's a shift being moved
        if (item.fromDate !== dateStr) {
          onDrop(item.shift, dateStr);
        }
      } else if ('employeeId' in item) {
        // It's an employee being added
        onEmployeeDrop(item.employeeId, dateStr, weekType);
      }
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
      canDrop: monitor.canDrop(),
    }),
  }), [dateStr, weekType]);

  const isToday = date.toDateString() === new Date().toDateString();
  
  return (
    <div
      ref={drop}
      onClick={() => onClick(date)}
      className={`border p-2 min-h-[120px] cursor-pointer transition-colors ${
        isOver ? 'bg-blue-50 border-blue-300' : 'hover:bg-gray-50'
      } ${isToday ? 'bg-blue-50/50' : ''}`}
    >
      <div className="font-medium text-sm mb-2 text-gray-700">
        {date.getDate()}
      </div>
      {dayShifts.map(shift => (
        <ShiftCard 
          key={shift.id} 
          shift={shift} 
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
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
            Schicht hinzufügen - {date?.toLocaleDateString('de-DE')}
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

    // Determine day of week
    const dateObj = new Date(date);
    const dayIndex = dateObj.getDay();
    const daysMap = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
    const dayOfWeek = daysMap[dayIndex] as keyof typeof employee['workingHours']['weekA'];
    const weekKey = weekType === 'A' ? 'weekA' : 'weekB';

    // Get employee's default working hours for this day
    const workingHours = employee.workingHours[weekKey][dayOfWeek];

    const newShift: Shift = {
      id: `${employeeId}-${date}-${Date.now()}`,
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

  // Generate calendar days
  const startDate = new Date(schedule.startDate);
  const endDate = new Date(schedule.endDate);
  const days: Date[] = [];
  
  let currentDate = new Date(startDate);
  while (currentDate <= endDate) {
    days.push(new Date(currentDate));
    currentDate.setDate(currentDate.getDate() + 1);
  }

  // Group by weeks for display
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

  const weekDays = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

  // Filter weekDays based on checkbox selections
  const visibleWeekDays = weekDays.filter((day, index) => {
    // index: 0=Mo, 1=Di, 2=Mi, 3=Do, 4=Fr, 5=Sa, 6=So
    if (index === 5 && !showSaturday) return false; // Saturday
    if (index === 6 && !showSunday) return false; // Sunday
    return true;
  });

  // Calculate grid columns based on visible days
  const gridCols = visibleWeekDays.length;
  const gridColsClass = `grid-cols-${gridCols}`;

  return (
    <DndProvider backend={HTML5Backend}>
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
              Samstagsarbeit anzeigen
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
              Sonntagsarbeit anzeigen
            </Label>
          </div>
        </div>

        <div className="border rounded-lg overflow-hidden">
          <div className="grid bg-gray-100 border-b" style={{ gridTemplateColumns: `repeat(${gridCols}, 1fr)` }}>
            {visibleWeekDays.map(day => (
              <div key={day} className="p-2 text-center font-medium text-sm">
                {day}
              </div>
            ))}
          </div>
          
          {weeks.map((week, weekIndex) => {
            // Determine week type based on the first day of the week
            const firstDayOfWeek = week[0];
            const referenceDate = new Date('2024-01-01');
            const weeksDiff = Math.floor((firstDayOfWeek.getTime() - referenceDate.getTime()) / (7 * 24 * 60 * 60 * 1000));
            const weekType: WeekType = weeksDiff % 2 === 0 ? 'A' : 'B';
            
            // Only show weeks that match the current week filter
            if (weekType !== currentWeek) {
              return null;
            }

            return (
              <div key={weekIndex} className="grid" style={{ gridTemplateColumns: `repeat(${gridCols}, 1fr)` }}>
                {week.map((day, dayIndex) => {
                  // Check if this day should be hidden based on checkbox filters
                  const dayOfWeek = day.getDay();
                  const isSaturday = dayOfWeek === 6;
                  const isSunday = dayOfWeek === 0;

                  if ((isSaturday && !showSaturday) || (isSunday && !showSunday)) {
                    return null;
                  }

                  // Fill empty cells at the start of the week
                  const emptyStart = weekIndex === 0 && dayIndex === 0
                    ? Array.from({ length: day.getDay() === 0 ? 6 : day.getDay() - 1 })
                    : [];

                  return (
                    <React.Fragment key={day.toISOString()}>
                      {emptyStart.map((_, i) => (
                        <div key={`empty-${i}`} className="border p-2 bg-gray-50 min-h-[120px]" />
                      ))}
                      <DayCell
                        date={day}
                        shifts={schedule.shifts}
                        weekType={weekType}
                        onDrop={handleDrop}
                        onEmployeeDrop={handleEmployeeDrop}
                        onClick={handleDayClick}
                        onEdit={handleEdit}
                        onDelete={handleDelete}
                      />
                    </React.Fragment>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>

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