import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Shift, WeekType } from '../types';
import { format, parseISO, eachDayOfInterval } from 'date-fns';
import { de } from 'date-fns/locale';
import { useMediaQuery } from '../lib/useMediaQuery';
import { Button } from './ui/button';
import { Coffee, LayoutGrid, CalendarDays } from 'lucide-react';

interface ScheduleCalendarProps {
  shifts: Shift[];
  startDate: string;
  endDate: string;
  currentWeek: WeekType;
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

export function ScheduleCalendar({ shifts, startDate, endDate, currentWeek }: ScheduleCalendarProps) {
  const { employees } = useApp();
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [viewMode, setViewMode] = useState<'timeline' | 'swimlane'>('swimlane');

  const start = parseISO(startDate);
  const end = parseISO(endDate);

  const days = eachDayOfInterval({ start, end });

  const filteredShifts = shifts.filter(s => s.week === currentWeek);

  const getShiftsForDate = (date: Date) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    return filteredShifts.filter(s => s.date === dateStr);
  };

  const getEmployee = (employeeId: string) => {
    return employees.find(e => e.id === employeeId);
  };

  const sortedEmployees = [...employees].sort((a, b) => a.name.localeCompare(b.name));

  if (isMobile) {
    const weekLabel = currentWeek === 'A' ? 'Woche A' : 'Woche B';
    return (
      <div className="space-y-4">
        <p className="text-sm text-gray-500">{weekLabel}</p>
        {filteredShifts.length === 0 ? (
          <p className="text-sm text-gray-400 italic">Keine Schichten</p>
        ) : (
          filteredShifts.map(shift => {
            const employee = getEmployee(shift.employeeId);
            return (
              <div
                key={shift.id}
                className="text-sm p-2 rounded border"
                style={{
                  backgroundColor: employee?.color + '20',
                  borderLeft: `3px solid ${employee?.color}`,
                }}
              >
                <div className="font-medium">{employee?.name}</div>
                <div className="text-gray-600">
                  {format(new Date(shift.date), 'd. MMM', { locale: de })} — {shift.startTime}–{shift.endTime}
                </div>
              </div>
            );
          })
        )}
      </div>
    );
  }

  const cols = isMobile ? 'grid-cols-1' : 'grid-cols-7';

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
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
      </div>

      {viewMode === 'swimlane' ? (
        <div className="space-y-6">
          {days.map((day) => {
            const dayShifts = getShiftsForDate(day);
            const isWeekend = day.getDay() === 0 || day.getDay() === 6;

            return (
              <div
                key={day.toISOString()}
                className={`border rounded-lg overflow-hidden ${isWeekend ? 'bg-gray-50' : 'bg-white'}`}
              >
                <div className="bg-gray-100 px-4 py-2 font-medium text-sm border-b">
                  {format(day, 'EEEE, d. MMMM', { locale: de })}
                </div>
                <div className="divide-y">
                  {sortedEmployees.map(employee => {
                    const employeeShifts = dayShifts.filter(s => s.employeeId === employee.id);

                    if (employeeShifts.length === 0) {
                      return (
                        <div key={employee.id} className="flex items-center px-4 py-2 text-sm">
                          <div className="w-40 shrink-0 font-medium text-gray-700 truncate">
                            <div
                              className="inline-block w-2 h-2 rounded-full mr-2"
                              style={{ backgroundColor: employee.color }}
                            />
                            {employee.name}
                          </div>
                          <div className="text-gray-400 italic text-xs">—</div>
                        </div>
                      );
                    }

                    return (
                      <div key={employee.id} className="px-4 py-2 text-sm">
                        <div className="flex items-center gap-3 mb-1.5">
                          <div className="w-40 shrink-0 font-medium text-gray-700 truncate">
                            <div
                              className="inline-block w-2 h-2 rounded-full mr-2"
                              style={{ backgroundColor: employee.color }}
                            />
                            {employee.name}
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2 ml-9">
                          {employeeShifts.map(shift => (
                            <div
                              key={shift.id}
                              className="flex items-center gap-2 text-xs px-2 py-1 rounded"
                              style={{
                                backgroundColor: employee.color + '20',
                                borderLeft: `3px solid ${employee.color}`,
                              }}
                            >
                              <span className="font-medium">{shift.startTime.slice(0, 5)}</span>
                              <span className="text-gray-400">–</span>
                              <span className="font-medium">{shift.endTime.slice(0, 5)}</span>
                              {shift.breakStart && shift.breakEnd && (
                                <span className="text-gray-400 flex items-center gap-0.5 ml-1">
                                  <Coffee className="h-3 w-3" />
                                  {shift.breakStart}–{shift.breakEnd}
                                </span>
                              )}
                              {shift.label && (
                                <span className="text-gray-500 ml-1">{shift.label}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
                {dayShifts.length === 0 && (
                  <div className="px-4 py-3 text-sm text-gray-400 italic">
                    Keine Schichten an diesem Tag
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <>
          {!isMobile && (
          <div className="grid grid-cols-7 gap-2">
            {['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'].map(day => (
              <div key={day} className="text-center font-medium text-sm text-gray-600 py-2">
                {day}
              </div>
            ))}
          </div>
          )}

          <div className={`grid ${cols} gap-2`}>
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
                          {shift.breakStart && shift.breakEnd && (
                            <div className="text-[10px] text-gray-400 flex items-center gap-0.5">
                              <Coffee className="h-2.5 w-2.5" /> {shift.breakStart}–{shift.breakEnd}
                            </div>
                          )}
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
        </>
      )}

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
