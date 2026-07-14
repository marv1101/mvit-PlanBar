import { Employee, Schedule } from '../types';
import { TIMEZONE } from './timezone';
import { toast } from 'sonner';

export function exportShiftsCSV(
  shifts: Schedule['shifts'],
  name: string,
  employees: Employee[],
) {
  if (shifts.length === 0) {
    toast.error('Keine Schichten zum Exportieren');
    return;
  }
  const headers = ['Datum', 'Woche', 'Mitarbeiter', 'Start', 'Ende', 'Pause Start', 'Pause Ende'];
  const rows = shifts.map(shift => {
    const employee = employees.find(e => e.id === shift.employeeId);
    return [
      new Date(shift.date).toLocaleDateString('de-DE', { timeZone: TIMEZONE }),
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
}
