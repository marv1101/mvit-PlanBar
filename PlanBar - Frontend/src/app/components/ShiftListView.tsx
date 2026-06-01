import { Pencil, Trash2 } from 'lucide-react';
import { Button } from './ui/button';
import { Shift, Employee } from '../types';
import { TIMEZONE } from '../lib/timezone';

interface ShiftListViewProps {
  shifts: Shift[];
  employees: Employee[];
  weekLabel: string;
  onEdit: (shift: Shift) => void;
  onDelete: (shift: Shift) => void;
}

export function ShiftListView({ shifts, employees, weekLabel, onEdit, onDelete }: ShiftListViewProps) {
  const grouped = shifts.reduce<Record<string, Shift[]>>((acc, shift) => {
    if (!acc[shift.date]) acc[shift.date] = [];
    acc[shift.date].push(shift);
    return acc;
  }, {});

  const sortedDates = Object.keys(grouped).sort();

  if (sortedDates.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        Keine Schichten für {weekLabel}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {sortedDates.map(date => {
        const dateObj = new Date(date + 'T00:00:00');
        const dayLabel = dateObj.toLocaleDateString('de-DE', { timeZone: TIMEZONE, weekday: 'long', day: 'numeric', month: 'long' });

        return (
          <div key={date} className="border rounded-lg overflow-hidden">
            <div className="bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700">
              {dayLabel}
            </div>
            <div className="divide-y">
              {grouped[date].map(shift => {
                const employee = employees.find(e => e.id === shift.employeeId);
                return (
                  <div key={shift.id} className="flex items-center gap-3 px-3 py-2.5">
                    <div
                      className="w-1 h-10 rounded-full flex-shrink-0"
                      style={{ backgroundColor: employee?.color || '#6b7280' }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className={`inline-flex items-center justify-center w-4 h-4 rounded text-[10px] font-bold leading-none text-white ${
                          shift.week === 'A' ? 'bg-blue-500' : 'bg-purple-500'
                        }`}>
                          {shift.week}
                        </span>
                        <span className="font-medium text-sm truncate">{employee?.name || 'Unbekannt'}</span>
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        {shift.startTime} – {shift.endTime}
                      </div>
                    </div>
                    <div className="flex gap-1 flex-shrink-0">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onEdit(shift)}
                        aria-label={`Schicht ${employee?.name || ''} ${shift.startTime}–${shift.endTime} bearbeiten`}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-red-600"
                        onClick={() => onDelete(shift)}
                        aria-label={`Schicht ${employee?.name || ''} ${shift.startTime}–${shift.endTime} löschen`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
