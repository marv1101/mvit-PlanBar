import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Checkbox } from '../components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Calendar, Sparkles, Download, Save, Eye, Trash2, CalendarDays } from 'lucide-react';
import { Schedule as ScheduleType, Shift, WeekType } from '../types';
import { ScheduleCalendar } from '../components/ScheduleCalendar';
import { EditableScheduleCalendar } from '../components/EditableScheduleCalendar';
import { toast } from 'sonner';

export function Schedule() {
  const { 
    employees, 
    requests, 
    schedules,
    addSchedule, 
    updateSchedule,
    deleteSchedule,
    currentWeek, 
    setCurrentWeek, 
    roles 
  } = useApp();

  const [activeTab, setActiveTab] = useState<'create' | 'manage'>('create');
  const [selectedSchedule, setSelectedSchedule] = useState<ScheduleType | null>(null);
  
  // Create schedule state
  const [scheduleName, setScheduleName] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [generatedShifts, setGeneratedShifts] = useState<Shift[]>([]);
  const [minEmployeesPerDay, setMinEmployeesPerDay] = useState(2);
  const [roleRequirements, setRoleRequirements] = useState<Record<string, number>>({});
  const [includeSaturday, setIncludeSaturday] = useState(true);
  const [includeSunday, setIncludeSunday] = useState(true);

  const handleRoleRequirementChange = (roleId: string, value: number) => {
    setRoleRequirements({ ...roleRequirements, [roleId]: value });
  };

  const generateSchedule = () => {
    if (!startDate || !endDate) {
      toast.error('Bitte Start- und Enddatum eingeben');
      return;
    }

    const start = new Date(startDate);
    const end = new Date(endDate);
    const shifts: Shift[] = [];

    // Track work hours per employee per week
    const employeeWeekHours: Record<string, Record<string, number>> = {};

    // Helper function to calculate shift duration in hours
    const calculateShiftHours = (startTime: string, endTime: string, breakStart?: string, breakEnd?: string) => {
      const [startH, startM] = startTime.split(':').map(Number);
      const [endH, endM] = endTime.split(':').map(Number);
      let workMinutes = (endH * 60 + endM) - (startH * 60 + startM);
      
      if (breakStart && breakEnd) {
        const [breakStartH, breakStartM] = breakStart.split(':').map(Number);
        const [breakEndH, breakEndM] = breakEnd.split(':').map(Number);
        const breakMinutes = (breakEndH * 60 + breakEndM) - (breakStartH * 60 + breakStartM);
        workMinutes -= breakMinutes;
      }
      
      return workMinutes / 60;
    };

    // Helper function to get week identifier (ISO week number + year)
    const getWeekIdentifier = (date: Date) => {
      const year = date.getFullYear();
      const weekNum = Math.floor((date.getTime() - new Date(year, 0, 1).getTime()) / (7 * 24 * 60 * 60 * 1000));
      return `${year}-W${weekNum}`;
    };

    // Get reference date for A/B week calculation (use a fixed Monday)
    const referenceDate = new Date('2024-01-01');
    
    let currentDate = new Date(start);
    
    while (currentDate <= end) {
      const dayIndex = currentDate.getDay();

      // Skip Saturday if not included
      if (dayIndex === 6 && !includeSaturday) {
        currentDate.setDate(currentDate.getDate() + 1);
        continue;
      }

      // Skip Sunday if not included
      if (dayIndex === 0 && !includeSunday) {
        currentDate.setDate(currentDate.getDate() + 1);
        continue;
      }

      const daysMap = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
      const dayOfWeek = daysMap[dayIndex] as keyof typeof employees[0]['workingHours']['weekA'];
      
      const weeksDiff = Math.floor((currentDate.getTime() - referenceDate.getTime()) / (7 * 24 * 60 * 60 * 1000));
      const weekType: WeekType = weeksDiff % 2 === 0 ? 'A' : 'B';
      const weekKey = weekType === 'A' ? 'weekA' : 'weekB';
      const weekId = getWeekIdentifier(currentDate);

      const availableEmployees = employees.filter(emp => {
        const workingHours = emp.workingHours[weekKey][dayOfWeek];
        if (!workingHours.enabled) return false;

        const dateStr = currentDate.toISOString().split('T')[0];
        const employeeRequests = requests.filter(
          req => req.employeeId === emp.id && req.date === dateStr && req.week === weekType
        );

        const hasBlockingRequest = employeeRequests.some(
          req => req.type === 'urlaubswunsch' || req.type === 'nicht-verfügbar'
        );
        
        if (hasBlockingRequest) return false;

        // Check if employee has reached max work hours for this week
        if (emp.maxWorkHours) {
          if (!employeeWeekHours[emp.id]) {
            employeeWeekHours[emp.id] = {};
          }
          
          const currentWeekHours = employeeWeekHours[emp.id][weekId] || 0;
          const shiftHours = calculateShiftHours(
            workingHours.start,
            workingHours.end,
            emp.breakTime.start,
            emp.breakTime.end
          );
          
          // Don't assign if it would exceed max hours
          if (currentWeekHours + shiftHours > emp.maxWorkHours) {
            return false;
          }
        }
        
        return true;
      });

      const dateStr = currentDate.toISOString().split('T')[0];
      const sortedEmployees = [...availableEmployees].sort((a, b) => {
        const aPreferred = requests.some(
          req => req.employeeId === a.id && req.date === dateStr && req.type === 'bevorzugt'
        );
        const bPreferred = requests.some(
          req => req.employeeId === b.id && req.date === dateStr && req.type === 'bevorzugt'
        );
        
        if (aPreferred && !bPreferred) return -1;
        if (!aPreferred && bPreferred) return 1;
        
        // Secondary sort: prefer employees with fewer hours this week
        const aWeekHours = employeeWeekHours[a.id]?.[weekId] || 0;
        const bWeekHours = employeeWeekHours[b.id]?.[weekId] || 0;
        return aWeekHours - bWeekHours;
      });

      const assignedEmployees: typeof employees = [];

      // First pass: assign employees to meet role requirements
      for (const roleId of Object.keys(roleRequirements)) {
        const requiredCount = roleRequirements[roleId];
        const employeesWithRole = sortedEmployees.filter(
          emp => emp.roles.includes(roleId) && !assignedEmployees.includes(emp)
        );

        for (let i = 0; i < Math.min(requiredCount, employeesWithRole.length); i++) {
          assignedEmployees.push(employeesWithRole[i]);
        }
      }

      // Second pass: fill up to minimum employees per day
      const remainingEmployees = sortedEmployees.filter(
        emp => !assignedEmployees.includes(emp)
      );
      const additionalNeeded = Math.max(0, minEmployeesPerDay - assignedEmployees.length);
      
      for (let i = 0; i < Math.min(additionalNeeded, remainingEmployees.length); i++) {
        assignedEmployees.push(remainingEmployees[i]);
      }

      // Create shifts for assigned employees and track hours
      assignedEmployees.forEach(emp => {
        const workingHours = emp.workingHours[weekKey][dayOfWeek];
        
        const shift: Shift = {
          id: `${emp.id}-${dateStr}-${Math.random()}`,
          employeeId: emp.id,
          date: dateStr,
          week: weekType,
          startTime: workingHours.start,
          endTime: workingHours.end,
          breakStart: emp.breakTime.start,
          breakEnd: emp.breakTime.end,
        };
        
        shifts.push(shift);
        
        // Update tracked hours
        if (!employeeWeekHours[emp.id]) {
          employeeWeekHours[emp.id] = {};
        }
        if (!employeeWeekHours[emp.id][weekId]) {
          employeeWeekHours[emp.id][weekId] = 0;
        }
        
        const shiftHours = calculateShiftHours(
          workingHours.start,
          workingHours.end,
          emp.breakTime.start,
          emp.breakTime.end
        );
        
        employeeWeekHours[emp.id][weekId] += shiftHours;
      });

      currentDate.setDate(currentDate.getDate() + 1);
    }

    setGeneratedShifts(shifts);
    toast.success(`Schichtplan mit ${shifts.length} Schichten erstellt`);
  };

  const saveSchedule = () => {
    if (!scheduleName || generatedShifts.length === 0) {
      toast.error('Bitte Namen eingeben und Schichtplan generieren');
      return;
    }

    const newSchedule: ScheduleType = {
      id: Date.now().toString(),
      name: scheduleName,
      startDate,
      endDate,
      shifts: generatedShifts,
      roleRequirements,
    };

    addSchedule(newSchedule);
    toast.success('Schichtplan gespeichert');
    
    // Switch to manage tab and select the new schedule
    setActiveTab('manage');
    setSelectedSchedule(newSchedule);
  };

  const exportSchedule = () => {
    if (generatedShifts.length === 0) {
      toast.error('Keine Schichten zum Exportieren');
      return;
    }

    const headers = ['Datum', 'Woche', 'Mitarbeiter', 'Start', 'Ende', 'Pause Start', 'Pause Ende'];
    const rows = generatedShifts.map(shift => {
      const employee = employees.find(e => e.id === shift.employeeId);
      return [
        new Date(shift.date).toLocaleDateString('de-DE'),
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
    link.download = `schichtplan-${scheduleName || 'export'}.csv`;
    link.click();
    
    toast.success('Schichtplan exportiert');
  };

  const handleViewSchedule = (schedule: ScheduleType) => {
    setSelectedSchedule(schedule);
  };

  const handleDeleteSchedule = (schedule: ScheduleType) => {
    if (confirm(`Möchten Sie den Schichtplan "${schedule.name}" wirklich löschen?`)) {
      deleteSchedule(schedule.id);
      if (selectedSchedule?.id === schedule.id) {
        setSelectedSchedule(null);
      }
      toast.success('Schichtplan gelöscht');
    }
  };

  const handleUpdateSchedule = (updatedSchedule: ScheduleType) => {
    updateSchedule(updatedSchedule.id, updatedSchedule);
  };

  const exportExistingSchedule = (schedule: ScheduleType) => {
    const headers = ['Datum', 'Woche', 'Mitarbeiter', 'Start', 'Ende', 'Pause Start', 'Pause Ende'];
    const rows = schedule.shifts.map(shift => {
      const employee = employees.find(e => e.id === shift.employeeId);
      return [
        new Date(shift.date).toLocaleDateString('de-DE'),
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
    link.download = `schichtplan-${schedule.name}.csv`;
    link.click();
    
    toast.success('Schichtplan exportiert');
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-semibold text-2xl mb-2">Schichtplanung</h2>
        <p className="text-gray-600">Erstellen und verwalten Sie Ihre Schichtpläne</p>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'create' | 'manage')}>
        <TabsList>
          <TabsTrigger value="create">
            <Sparkles className="h-4 w-4 mr-2" />
            Neu erstellen
          </TabsTrigger>
          <TabsTrigger value="manage">
            <CalendarDays className="h-4 w-4 mr-2" />
            Verwalten ({schedules.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="create" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Schichtplan-Einstellungen</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="scheduleName">Plan-Name</Label>
                <Input
                  id="scheduleName"
                  value={scheduleName}
                  onChange={(e) => setScheduleName(e.target.value)}
                  placeholder="z.B. April 2026"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="startDate">Startdatum</Label>
                  <Input
                    id="startDate"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>
                <div>
                  <Label htmlFor="endDate">Enddatum</Label>
                  <Input
                    id="endDate"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="minEmployees">Mindestanzahl Mitarbeiter pro Tag</Label>
                <Input
                  id="minEmployees"
                  type="number"
                  min="1"
                  value={minEmployeesPerDay}
                  onChange={(e) => setMinEmployeesPerDay(parseInt(e.target.value))}
                />
              </div>

              <div className="space-y-2">
                <Label>Wochenendarbeit</Label>
                <div className="flex gap-6 p-3 bg-gray-50 border border-gray-200 rounded-md">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="include-saturday"
                      checked={includeSaturday}
                      onCheckedChange={(checked) => setIncludeSaturday(checked as boolean)}
                    />
                    <Label
                      htmlFor="include-saturday"
                      className="text-sm font-normal cursor-pointer"
                    >
                      Samstagsarbeit
                    </Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="include-sunday"
                      checked={includeSunday}
                      onCheckedChange={(checked) => setIncludeSunday(checked as boolean)}
                    />
                    <Label
                      htmlFor="include-sunday"
                      className="text-sm font-normal cursor-pointer"
                    >
                      Sonntagsarbeit
                    </Label>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Rollenanforderungen pro Tag</Label>
                <div className="grid grid-cols-2 gap-4">
                  {roles.map(role => (
                    <div key={role.id}>
                      <Label htmlFor={`role-${role.id}`} className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: role.color }}
                        />
                        {role.name}
                      </Label>
                      <Input
                        id={`role-${role.id}`}
                        type="number"
                        min="0"
                        value={roleRequirements[role.id] || 0}
                        onChange={(e) => handleRoleRequirementChange(role.id, parseInt(e.target.value) || 0)}
                      />
                    </div>
                  ))}
                  {roles.length === 0 && (
                    <p className="text-sm text-gray-500 col-span-2">Keine Rollen verfügbar. Bitte erstellen Sie zuerst Rollen.</p>
                  )}
                </div>
              </div>

              <div className="flex gap-3">
                <Button onClick={generateSchedule} className="flex-1">
                  <Sparkles className="h-4 w-4 mr-2" />
                  Automatisch generieren
                </Button>
                <Button onClick={saveSchedule} variant="outline">
                  <Save className="h-4 w-4 mr-2" />
                  Speichern
                </Button>
                <Button onClick={exportSchedule} variant="outline">
                  <Download className="h-4 w-4 mr-2" />
                  Exportieren
                </Button>
              </div>
            </CardContent>
          </Card>

          {generatedShifts.length > 0 && (
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle>Vorschau</CardTitle>
                  <Tabs value={currentWeek} onValueChange={(v) => setCurrentWeek(v as WeekType)}>
                    <TabsList>
                      <TabsTrigger value="A">Woche A</TabsTrigger>
                      <TabsTrigger value="B">Woche B</TabsTrigger>
                    </TabsList>
                  </Tabs>
                </div>
              </CardHeader>
              <CardContent>
                <ScheduleCalendar 
                  shifts={generatedShifts} 
                  startDate={startDate} 
                  endDate={endDate}
                  currentWeek={currentWeek}
                />
              </CardContent>
            </Card>
          )}

          {generatedShifts.length === 0 && (
            <Card>
              <CardContent className="py-12 text-center">
                <Calendar className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 mb-2">Noch kein Schichtplan erstellt</p>
                <p className="text-sm text-gray-500">
                  Geben Sie die Einstellungen ein und klicken Sie auf "Automatisch generieren"
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="manage" className="space-y-6">
          {schedules.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <CalendarDays className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 mb-2">Keine gespeicherten Schichtpläne</p>
                <p className="text-sm text-gray-500 mb-4">
                  Erstellen Sie Ihren ersten Schichtplan im Tab "Neu erstellen"
                </p>
                <Button onClick={() => setActiveTab('create')}>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Schichtplan erstellen
                </Button>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {schedules.map((schedule) => (
                  <Card 
                    key={schedule.id}
                    className={`cursor-pointer transition-all ${
                      selectedSchedule?.id === schedule.id 
                        ? 'ring-2 ring-blue-500 shadow-lg' 
                        : 'hover:shadow-md'
                    }`}
                  >
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Calendar className="h-5 w-5 text-blue-600" />
                        {schedule.name}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2 text-sm text-gray-600 mb-4">
                        <p>
                          {new Date(schedule.startDate).toLocaleDateString('de-DE')} - {new Date(schedule.endDate).toLocaleDateString('de-DE')}
                        </p>
                        <p>{schedule.shifts.length} Schichten</p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant={selectedSchedule?.id === schedule.id ? "default" : "outline"}
                          onClick={() => handleViewSchedule(schedule)}
                          className="flex-1"
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          {selectedSchedule?.id === schedule.id ? 'Ausgewählt' : 'Ansehen'}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => exportExistingSchedule(schedule)}
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleDeleteSchedule(schedule)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {selectedSchedule && (
                <Card>
                  <CardHeader>
                    <div className="flex justify-between items-center">
                      <CardTitle>{selectedSchedule.name}</CardTitle>
                      <Tabs value={currentWeek} onValueChange={(v) => setCurrentWeek(v as WeekType)}>
                        <TabsList>
                          <TabsTrigger value="A">Woche A</TabsTrigger>
                          <TabsTrigger value="B">Woche B</TabsTrigger>
                        </TabsList>
                      </Tabs>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <EditableScheduleCalendar
                      schedule={selectedSchedule}
                      currentWeek={currentWeek}
                      onUpdateSchedule={handleUpdateSchedule}
                    />
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}