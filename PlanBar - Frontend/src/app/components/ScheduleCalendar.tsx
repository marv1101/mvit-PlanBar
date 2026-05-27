import React from 'react';
import { useApp } from '../context/AppContext';
import { Shift, WeekType } from '../types';
import { format, parseISO, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, startOfWeek, endOfWeek } from 'date-fns';
import { de } from 'date-fns/locale';

interface ScheduleCalendarProps {
  shifts: Shift[];
  startDate: string;
  endDate: string;
  currentWeek: WeekType;
}

export function ScheduleCalendar({ shifts, startDate, endDate, currentWeek }: ScheduleCalendarProps) {
  const { employees } = useApp();

  const start = parseISO(startDate);
  const end = parseISO(endDate);
  
  // Get all days in the range
  const days = eachDayOfInterval({ start, end });
  
  // Filter shifts for current week type
  const filteredShifts = shifts.filter(s => s.week === currentWeek);

  const getShiftsForDate = (date: Date) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    return filteredShifts.filter(s => s.date === dateStr);
  };

  const getEmployee = (employeeId: string) => {
    return employees.find(e => e.id === employeeId);
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-7 gap-2">
        {['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'].map(day => (
          <div key={day} className="text-center font-medium text-sm text-gray-600 py-2">
            {day}
          </div>
        ))}
      </div>
      
      <div className="grid grid-cols-7 gap-2">
        {days.map((day, index) => {
          const dayShifts = getShiftsForDate(day);
          const isWeekend = day.getDay() === 0 || day.getDay() === 6;
          
          return (
            <div
              key={index}
              className={`min-h-[120px] border rounded-lg p-2 ${
                isWeekend ? 'bg-gray-50' : 'bg-white'
              }`}
            >
              <div className="text-sm font-medium mb-2">
                {format(day, 'd. MMM', { locale: de })}
              </div>
              <div className="space-y-1">
                {dayShifts.map((shift) => {
                  const employee = getEmployee(shift.employeeId);
                  return (
                    <div
                      key={shift.id}
                      className="text-xs p-1.5 rounded"
                      style={{
                        backgroundColor: employee?.color + '20',
                        borderLeft: `3px solid ${employee?.color}`,
                      }}
                    >
                      <div className="font-medium truncate flex items-center gap-1">
                        <span className={`inline-flex items-center justify-center w-3.5 h-3.5 rounded text-[9px] font-bold leading-none ${
                          shift.week === 'A' ? 'bg-blue-500 text-white' : 'bg-purple-500 text-white'
                        }`}>
                          {shift.week}
                        </span>
                        {employee?.name.split(' ')[0]}
                      </div>
                      <div className="text-gray-600">
                        {shift.startTime.slice(0, 5)} - {shift.endTime.slice(0, 5)}
                      </div>
                    </div>
                  );
                })}
                {dayShifts.length === 0 && (
                  <div className="text-xs text-gray-400 italic">
                    Keine Schichten
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex flex-wrap gap-4 pt-4 border-t">
        <div className="text-sm font-medium">Legende:</div>
        {employees.map((employee) => (
          <div key={employee.id} className="flex items-center gap-2">
            <div
              className="w-4 h-4 rounded"
              style={{ backgroundColor: employee.color }}
            />
            <span className="text-sm">{employee.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
