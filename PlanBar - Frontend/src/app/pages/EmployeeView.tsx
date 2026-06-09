import React, { useState, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { User, Calendar, Clock, Coffee, Download, Loader2 } from 'lucide-react';
import { getWeekType } from '../lib/week';
import { WeekType, Shift } from '../types';
import { toast } from 'sonner';
import { TIMEZONE } from '../lib/timezone';
import { TimeAccountCard } from '../components/TimeAccountCard';

export function EmployeeView() {
  const { employees, schedules, roles, loading } = useApp();
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>('');
  const [selectedScheduleId, setSelectedScheduleId] = useState<string>('');
  const [currentWeek, setCurrentWeek] = useState<WeekType>('A');

  const selectedEmployee = useMemo(() => 
    employees.find(e => e.id === selectedEmployeeId),
    [employees, selectedEmployeeId]
  );

  const visibleSchedules = useMemo(() =>
    schedules.filter(s => s.status === 'review' || s.status === 'completed'),
    [schedules]
  );

  const selectedSchedule = useMemo(() => 
    visibleSchedules.find(s => s.id === selectedScheduleId),
    [visibleSchedules, selectedScheduleId]
  );

  const employeeShifts = useMemo(() => {
    if (!selectedSchedule || !selectedEmployeeId) return [];
    return selectedSchedule.shifts
      .filter(shift => shift.employeeId === selectedEmployeeId)
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }, [selectedSchedule, selectedEmployeeId]);

  const employeeShiftsByWeek = useMemo(() => {
    return employeeShifts.filter(shift => shift.week === currentWeek);
  }, [employeeShifts, currentWeek]);

  // Calculate statistics
  const statistics = useMemo(() => {
    if (employeeShifts.length === 0) {
      return {
        totalShifts: 0,
        totalHours: 0,
        avgHoursPerShift: 0,
        weekAShifts: 0,
        weekBShifts: 0,
      };
    }

    const calculateHours = (shift: Shift) => {
      const [startH, startM] = shift.startTime.split(':').map(Number);
      const [endH, endM] = shift.endTime.split(':').map(Number);
      const startMinutes = startH * 60 + startM;
      const endMinutes = endH * 60 + endM;
      let workMinutes = endMinutes - startMinutes;

      // Subtract break time if exists
      if (shift.breakStart && shift.breakEnd) {
        const [breakStartH, breakStartM] = shift.breakStart.split(':').map(Number);
        const [breakEndH, breakEndM] = shift.breakEnd.split(':').map(Number);
        const breakMinutes = (breakEndH * 60 + breakEndM) - (breakStartH * 60 + breakStartM);
        workMinutes -= breakMinutes;
      }

      return workMinutes / 60;
    };

    const totalHours = employeeShifts.reduce((sum, shift) => sum + calculateHours(shift), 0);
    const weekAShifts = employeeShifts.filter(s => s.week === 'A').length;
    const weekBShifts = employeeShifts.filter(s => s.week === 'B').length;

    return {
      totalShifts: employeeShifts.length,
      totalHours: totalHours.toFixed(1),
      avgHoursPerShift: (totalHours / employeeShifts.length).toFixed(1),
      weekAShifts,
      weekBShifts,
    };
  }, [employeeShifts]);

  // Group shifts by date for calendar view
  const shiftsByDate = useMemo(() => {
    const grouped: Record<string, Shift[]> = {};
    employeeShiftsByWeek.forEach(shift => {
      if (!grouped[shift.date]) {
        grouped[shift.date] = [];
      }
      grouped[shift.date].push(shift);
    });
    return grouped;
  }, [employeeShiftsByWeek]);

  // Generate calendar days for the selected schedule
  const calendarDays = useMemo(() => {
    if (!selectedSchedule) return [];
    
    const days: Date[] = [];
    const start = new Date(selectedSchedule.startDate);
    const end = new Date(selectedSchedule.endDate);
    
    let currentDate = new Date(start);
    while (currentDate <= end) {
      days.push(new Date(currentDate));
      currentDate.setDate(currentDate.getDate() + 1);
    }
    
    return days;
  }, [selectedSchedule]);

  // Group calendar days by weeks
  const calendarWeeks = useMemo(() => {
    const weeks: Date[][] = [];
    let currentWeekDays: Date[] = [];
    
    calendarDays.forEach((day, index) => {
      if (day.getDay() === 1 && currentWeekDays.length > 0) {
        weeks.push(currentWeekDays);
        currentWeekDays = [];
      }
      currentWeekDays.push(day);
      
      if (index === calendarDays.length - 1) {
        weeks.push(currentWeekDays);
      }
    });
    
    return weeks;
  }, [calendarDays]);

  const exportPersonalSchedule = () => {
    if (!selectedEmployee || employeeShifts.length === 0) {
      toast.error('Keine Schichten zum Exportieren');
      return;
    }

    const headers = ['Datum', 'Wochentag', 'Woche', 'Start', 'Ende', 'Pause Start', 'Pause Ende', 'Arbeitszeit (h)'];
    const rows = employeeShifts.map(shift => {
      const date = new Date(shift.date);
      const weekday = date.toLocaleDateString('de-DE', { timeZone: TIMEZONE, weekday: 'long' });
      
      const [startH, startM] = shift.startTime.split(':').map(Number);
      const [endH, endM] = shift.endTime.split(':').map(Number);
      let workMinutes = (endH * 60 + endM) - (startH * 60 + startM);
      
      if (shift.breakStart && shift.breakEnd) {
        const [breakStartH, breakStartM] = shift.breakStart.split(':').map(Number);
        const [breakEndH, breakEndM] = shift.breakEnd.split(':').map(Number);
        const breakMinutes = (breakEndH * 60 + breakEndM) - (breakStartH * 60 + breakStartM);
        workMinutes -= breakMinutes;
      }
      
      const hours = (workMinutes / 60).toFixed(1);

      return [
        date.toLocaleDateString('de-DE', { timeZone: TIMEZONE }),
        weekday,
        shift.week,
        shift.startTime,
        shift.endTime,
        shift.breakStart || '',
        shift.breakEnd || '',
        hours,
      ];
    });

    const csvContent = [headers, ...rows].map(row => row.join(';')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `schichtplan-${selectedEmployee.name}-${selectedSchedule?.name || 'export'}.csv`;
    link.click();
    
    toast.success('Persönlicher Schichtplan exportiert');
  };

  const weekDays = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="font-semibold text-2xl mb-2">Mitarbeiteransicht</h2>
          <p className="text-gray-600">Persönliche Schichtübersicht für Mitarbeiter</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-8 w-8 mx-auto text-blue-600 mb-4 animate-spin" />
            <p className="text-gray-600">Lade Daten...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-semibold text-2xl mb-2">Mitarbeiteransicht</h2>
        <p className="text-gray-600">Persönliche Schichtübersicht für Mitarbeiter</p>
      </div>

      {/* Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Auswahl</CardTitle>
          <CardDescription>Wählen Sie einen Mitarbeiter und Schichtplan aus</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="employee">Mitarbeiter</Label>
              <select
                id="employee"
                className="w-full border rounded-md px-3 py-2 mt-1"
                value={selectedEmployeeId}
                onChange={(e) => setSelectedEmployeeId(e.target.value)}
              >
                <option value="">Bitte wählen...</option>
                {employees.map(emp => (
                  <option key={emp.id} value={emp.id}>{emp.name}</option>
                ))}
              </select>
            </div>

            <div>
              <Label htmlFor="schedule">Schichtplan</Label>
              <select
                id="schedule"
                className="w-full border rounded-md px-3 py-2 mt-1"
                value={selectedScheduleId}
                onChange={(e) => setSelectedScheduleId(e.target.value)}
              >
                <option value="">Bitte wählen...</option>
                {visibleSchedules.map(schedule => (
                  <option key={schedule.id} value={schedule.id}>
                    {schedule.name} ({new Date(schedule.startDate).toLocaleDateString('de-DE', { timeZone: TIMEZONE })} - {new Date(schedule.endDate).toLocaleDateString('de-DE', { timeZone: TIMEZONE })})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {selectedEmployee && selectedSchedule && (
            <Button onClick={exportPersonalSchedule} variant="outline" className="w-full">
              <Download className="h-4 w-4 mr-2" />
              Persönlichen Schichtplan exportieren
            </Button>
          )}
        </CardContent>
      </Card>

      {selectedEmployee && selectedSchedule && (
        <>
          {/* Employee Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                {selectedEmployee.name}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4">
                <div>
                  <p className="text-sm text-gray-600">Rollen</p>
                  <div className="flex gap-2 mt-1">
                    {selectedEmployee.roles.map(roleId => {
                      const role = roles.find(r => r.id === roleId);
                      return role ? (
                        <div
                          key={role.id}
                          className="px-3 py-1 rounded-full text-sm font-medium text-white"
                          style={{ backgroundColor: role.color }}
                        >
                          {role.name}
                        </div>
                      ) : null;
                    })}
                    {selectedEmployee.roles.length === 0 && (
                      <span className="text-gray-400">Keine Rollen</span>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Statistics */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Card>
              <CardContent className="pt-6">
                <p className="text-2xl font-semibold">{statistics.totalShifts}</p>
                <p className="text-sm text-gray-600 mt-1">Gesamt Schichten</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-2xl font-semibold">{statistics.totalHours}h</p>
                <p className="text-sm text-gray-600 mt-1">Gesamt Stunden</p>
                {selectedEmployee.maxWorkHours && (
                  <p className="text-xs text-gray-500 mt-1">
                    Max: {selectedEmployee.maxWorkHours}h/Woche
                  </p>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-2xl font-semibold">{statistics.avgHoursPerShift}h</p>
                <p className="text-sm text-gray-600 mt-1">⌀ Stunden/Schicht</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-2xl font-semibold">{statistics.weekAShifts}</p>
                <p className="text-sm text-gray-600 mt-1">Woche A Schichten</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <p className="text-2xl font-semibold">{statistics.weekBShifts}</p>
                <p className="text-sm text-gray-600 mt-1">Woche B Schichten</p>
              </CardContent>
            </Card>
          </div>

          {/* Time Account */}
          <TimeAccountCard employeeId={selectedEmployeeId} />

          {/* Schedule View */}
          <Tabs value={currentWeek} onValueChange={(v) => setCurrentWeek(v as WeekType)}>
            <TabsList className="w-full">
              <TabsTrigger value="A" className="flex-1">Woche A</TabsTrigger>
              <TabsTrigger value="B" className="flex-1">Woche B</TabsTrigger>
            </TabsList>

            <TabsContent value={currentWeek} className="space-y-6">
              {/* Calendar View */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Calendar className="h-5 w-5" />
                    Kalenderansicht - Woche {currentWeek}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="border rounded-lg overflow-x-auto">
                    <div className="min-w-[700px]">
                      <div className="grid grid-cols-7 bg-gray-100 border-b">
                      {weekDays.map(day => (
                        <div key={day} className="p-2 text-center font-medium text-sm">
                          {day}
                        </div>
                      ))}
                    </div>
                    
                    {calendarWeeks.map((week, weekIndex) => {
                      // Determine week type
                      const weekType = getWeekType(week[0]);
                      
                      if (weekType !== currentWeek) return null;

                      return (
                        <div key={weekIndex} className="grid grid-cols-7">
                          {week.map((day, dayIndex) => {
                            const emptyStart = weekIndex === 0 && dayIndex === 0 
                              ? Array.from({ length: day.getDay() === 0 ? 6 : day.getDay() - 1 })
                              : [];
                            
                            const dateStr = day.toISOString().split('T')[0];
                            const dayShifts = shiftsByDate[dateStr] || [];
                            const isToday = day.toDateString() === new Date().toDateString();

                            return (
                              <React.Fragment key={day.toISOString()}>
                                {emptyStart.map((_, i) => (
                                  <div key={`empty-${i}`} className="border p-2 bg-gray-50 min-h-[100px]" />
                                ))}
                                <div
                                  className={`border p-2 min-h-[100px] ${
                                    isToday ? 'bg-blue-50' : ''
                                  } ${dayShifts.length > 0 ? 'bg-green-50' : ''}`}
                                >
                                  <div className="font-medium text-sm mb-2 text-gray-700">
                                    {day.getDate()}
                                  </div>
                                  {dayShifts.map(shift => (
                                    <div
                                      key={shift.id}
                                      className="p-2 rounded text-xs mb-1"
                                      style={{ 
                                        backgroundColor: selectedEmployee.color + '20', 
                                        borderLeft: `3px solid ${selectedEmployee.color}` 
                                      }}
                                    >
                                      <div className="font-medium flex items-center gap-1" style={{ color: selectedEmployee.color }}>
                                        <span className={`inline-flex items-center justify-center w-3.5 h-3.5 rounded text-[9px] font-bold leading-none ${
                                          shift.week === 'A' ? 'bg-blue-500 text-white' : 'bg-purple-500 text-white'
                                        }`}>
                                          {shift.week}
                                        </span>
                                        {shift.startTime} - {shift.endTime}
                                      </div>
                                      {shift.breakStart && shift.breakEnd && (
                                        <div className="text-gray-600 flex items-center gap-1 mt-1">
                                          <Coffee className="h-3 w-3" />
                                          {shift.breakStart} - {shift.breakEnd}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </React.Fragment>
                            );
                          })}
                        </div>
                      );
                    })}
                  </div>
                </div>
                </CardContent>
              </Card>

              {/* List View */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="h-5 w-5" />
                    Schichtenliste - Woche {currentWeek}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {employeeShiftsByWeek.length > 0 ? (
                    <div className="space-y-3">
                      {employeeShiftsByWeek.map(shift => {
                        const date = new Date(shift.date);
                        const weekday = date.toLocaleDateString('de-DE', { timeZone: TIMEZONE, weekday: 'long' });
                        
                        return (
                          <div
                            key={shift.id}
                            className="border rounded-lg p-4"
                            style={{ borderLeftWidth: '4px', borderLeftColor: selectedEmployee.color }}
                          >
                            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                              <div>
                                <p className="font-semibold">
                                  {date.toLocaleDateString('de-DE', { timeZone: TIMEZONE })} - {weekday}
                                </p>
                                <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
                                  <div className="flex items-center gap-1">
                                    <span className={`inline-flex items-center justify-center w-4 h-4 rounded text-[10px] font-bold leading-none ${
                                      shift.week === 'A' ? 'bg-blue-500 text-white' : 'bg-purple-500 text-white'
                                    }`}>
                                      {shift.week}
                                    </span>
                                    <Clock className="h-4 w-4" />
                                    {shift.startTime} - {shift.endTime}
                                  </div>
                                  {shift.breakStart && shift.breakEnd && (
                                    <div className="flex items-center gap-1">
                                      <Coffee className="h-4 w-4" />
                                      Pause: {shift.breakStart} - {shift.breakEnd}
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-8">
                      Keine Schichten in Woche {currentWeek}
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}

      {(!selectedEmployee || !selectedSchedule) && (
        <Card>
          <CardContent className="py-12 text-center">
            <User className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-600 mb-2">Keine Auswahl getroffen</p>
            <p className="text-sm text-gray-500">
              Bitte wählen Sie einen Mitarbeiter und einen Schichtplan aus, um die persönlichen Schichten anzuzeigen.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}