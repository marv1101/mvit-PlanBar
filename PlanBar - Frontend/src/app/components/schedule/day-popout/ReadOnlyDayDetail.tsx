import { Coffee, CalendarOff } from 'lucide-react';
import { Shift, Employee } from '../../../types';
import { TIMEZONE } from '../../../lib/timezone';

interface ReadOnlyDayDetailProps {
  date: Date;
  shifts: Shift[];
  employees: Employee[];
}

export function ReadOnlyDayDetail({ date, shifts, employees }: ReadOnlyDayDetailProps) {
  const weekday = date.toLocaleDateString('de-DE', { timeZone: TIMEZONE, weekday: 'long' });
  const sorted = [...shifts].sort((a, b) => a.startTime.localeCompare(b.startTime));

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">{weekday}</p>
      {sorted.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400">
          <CalendarOff className="h-12 w-12 mb-3 opacity-50" />
          <p className="font-medium">Keine Schichten an diesem Tag</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {sorted.map(shift => {
            const employee = employees.find(e => e.id === shift.employeeId);
            const color = employee?.color || '#3b82f6';
            return (
              <div
                key={shift.id}
                className="rounded-lg border p-5 shadow-sm"
                style={{ borderLeft: `6px solid ${color}`, backgroundColor: color + '10' }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className={`inline-flex items-center justify-center w-5 h-5 rounded text-xs font-bold leading-none ${
                      shift.week === 'A' ? 'bg-blue-500 text-white' : 'bg-purple-500 text-white'
                    }`}
                  >
                    {shift.week}
                  </span>
                  {employee && (
                    <span className="font-semibold" style={{ color }}>
                      {employee.name}
                    </span>
                  )}
                </div>
                <p className="text-3xl font-semibold tabular-nums">
                  {shift.startTime} - {shift.endTime}
                </p>
                {shift.breakStart && shift.breakEnd && (
                  <p className="mt-2 text-sm text-gray-600 flex items-center gap-1.5">
                    <Coffee className="h-4 w-4" /> Pause: {shift.breakStart} - {shift.breakEnd}
                  </p>
                )}
                {shift.label && (
                  <p className="mt-2 text-sm text-gray-500">{shift.label}</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
