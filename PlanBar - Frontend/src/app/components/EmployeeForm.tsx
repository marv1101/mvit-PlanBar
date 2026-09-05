import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Employee } from '../types';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Switch } from './ui/switch';
import { Checkbox } from './ui/checkbox';
import * as teamService from '../services/teamService';
import type { Team } from '../types';

interface EmployeeFormProps {
  employee: Employee | null;
  onClose: () => void;
}

const daysOfWeek = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'] as const;
const dayLabels: Record<typeof daysOfWeek[number], string> = {
  monday: 'Montag',
  tuesday: 'Dienstag',
  wednesday: 'Mittwoch',
  thursday: 'Donnerstag',
  friday: 'Freitag',
  saturday: 'Samstag',
  sunday: 'Sonntag',
};

const defaultWorkingHours = {
  weekA: {
    monday: { start: '08:00', end: '18:00', enabled: true },
    tuesday: { start: '08:00', end: '18:00', enabled: true },
    wednesday: { start: '08:00', end: '18:00', enabled: true },
    thursday: { start: '08:00', end: '18:00', enabled: true },
    friday: { start: '08:00', end: '18:00', enabled: true },
    saturday: { start: '08:00', end: '14:00', enabled: true },
    sunday: { start: '09:00', end: '13:00', enabled: false },
  },
  weekB: {
    monday: { start: '08:00', end: '18:00', enabled: true },
    tuesday: { start: '08:00', end: '18:00', enabled: true },
    wednesday: { start: '08:00', end: '18:00', enabled: true },
    thursday: { start: '08:00', end: '18:00', enabled: true },
    friday: { start: '08:00', end: '18:00', enabled: true },
    saturday: { start: '08:00', end: '14:00', enabled: true },
    sunday: { start: '09:00', end: '13:00', enabled: false },
  },
};

const colors = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#14b8a6', '#f97316', '#06b6d4', '#84cc16'
];

export function EmployeeForm({ employee, onClose }: EmployeeFormProps) {
  const { addEmployee, updateEmployee, roles } = useApp();
  const [allTeams, setAllTeams] = useState<Team[]>([]);
  const [formData, setFormData] = useState<Employee>(() =>
    employee || {
      id: Date.now().toString(),
      name: '',
      email: '',
      roles: [],
      workingHours: defaultWorkingHours,
      breakTime: { start: '12:00', end: '13:00', duration: 60 },
      color: colors[0],
      maxWorkHours: 40,
      teamIds: [],
    }
  );

  React.useEffect(() => {
    if (employee) {
      setFormData(employee);
    }
  }, [employee]);

  React.useEffect(() => {
    teamService.getTeams().then(res => setAllTeams(res.items)).catch(() => {});
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (employee) {
      updateEmployee(employee.id, formData);
    } else {
      addEmployee(formData);
    }
    onClose();
  };

  const handleWorkingHoursChange = (
    week: 'weekA' | 'weekB',
    day: typeof daysOfWeek[number],
    field: 'start' | 'end' | 'enabled',
    value: string | boolean
  ) => {
    setFormData({
      ...formData,
      workingHours: {
        ...formData.workingHours,
        [week]: {
          ...formData.workingHours[week],
          [day]: {
            ...formData.workingHours[week][day],
            [field]: value,
          },
        },
      },
    });
  };

  const handleRoleToggle = (roleId: string) => {
    const newRoles = formData.roles.includes(roleId)
      ? formData.roles.filter(r => r !== roleId)
      : [...formData.roles, roleId];
    setFormData({ ...formData, roles: newRoles });
  };

  const handleTeamToggle = (teamId: number) => {
    const current = formData.teamIds ?? [];
    const newTeamIds = current.includes(teamId)
      ? current.filter(id => id !== teamId)
      : [...current, teamId];
    setFormData({ ...formData, teamIds: newTeamIds });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-4">
        <div>
          <Label htmlFor="name">Name</Label>
          <Input
            id="name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />
        </div>

        <div>
          <Label htmlFor="email">E-Mail</Label>
          <Input
            id="email"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            required
          />
        </div>

        <div>
          <Label className="mb-3 block">Rollen / Fähigkeiten</Label>
          <div className="space-y-2">
            {roles.map((role) => (
              <div key={role.id} className="flex items-center space-x-2">
                <Checkbox
                  id={`role-${role.id}`}
                  checked={formData.roles.includes(role.id)}
                  onCheckedChange={() => handleRoleToggle(role.id)}
                />
                <Label htmlFor={`role-${role.id}`} className="font-normal cursor-pointer flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: role.color }}
                  />
                  {role.name}
                </Label>
              </div>
            ))}
            {roles.length === 0 && (
              <p className="text-sm text-gray-500">Keine Rollen verfügbar. Bitte erstellen Sie zuerst Rollen.</p>
            )}
          </div>
        </div>

        <div>
          <Label className="mb-3 block">Teams</Label>
          <div className="space-y-2">
            {allTeams.map((team) => (
              <div key={team.id} className="flex items-center space-x-2">
                <Checkbox
                  id={`team-${team.id}`}
                  checked={(formData.teamIds ?? []).includes(Number(team.id))}
                  onCheckedChange={() => handleTeamToggle(Number(team.id))}
                />
                <Label htmlFor={`team-${team.id}`} className="font-normal cursor-pointer flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: team.color || '#9ca3af' }}
                  />
                  {team.name}
                </Label>
              </div>
            ))}
            {allTeams.length === 0 && (
              <p className="text-sm text-gray-500">Keine Teams verfügbar. Bitte erstellen Sie zuerst Teams.</p>
            )}
          </div>
        </div>

        <div>
          <Label>Farbe</Label>
          <div className="flex gap-2 mt-2" role="radiogroup" aria-label="Farbe auswählen">
            {colors.map((color) => (
              <button
                key={color}
                type="button"
                className={`w-8 h-8 rounded-full border-2 ${
                  formData.color === color ? 'border-gray-900' : 'border-gray-300'
                }`}
                style={{ backgroundColor: color }}
                onClick={() => setFormData({ ...formData, color })}
                aria-label={`Farbe ${color}`}
                aria-checked={formData.color === color}
                role="radio"
              />
            ))}
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <Label htmlFor="breakStart">Pause Start</Label>
            <Input
              id="breakStart"
              type="time"
              value={formData.breakTime.start}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  breakTime: { ...formData.breakTime, start: e.target.value },
                })
              }
            />
          </div>
          <div>
            <Label htmlFor="breakEnd">Pause Ende</Label>
            <Input
              id="breakEnd"
              type="time"
              value={formData.breakTime.end}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  breakTime: { ...formData.breakTime, end: e.target.value },
                })
              }
            />
          </div>
          <div>
            <Label htmlFor="breakDuration">Dauer (Min.)</Label>
            <Input
              id="breakDuration"
              type="number"
              value={formData.breakTime.duration}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  breakTime: { ...formData.breakTime, duration: parseInt(e.target.value) },
                })
              }
            />
          </div>
        </div>

        <div>
          <Label htmlFor="maxWorkHours">Maximale Arbeitszeit pro Woche (Stunden)</Label>
          <Input
            id="maxWorkHours"
            type="number"
            min="0"
            max="168"
            step="0.5"
            value={formData.maxWorkHours || 40}
            onChange={(e) =>
              setFormData({
                ...formData,
                maxWorkHours: parseFloat(e.target.value) || undefined,
              })
            }
            placeholder="z.B. 40"
          />
          <p className="text-xs text-gray-500 mt-1">
            Legen Sie die maximale Wochenarbeitszeit fest. Der Generator berücksichtigt diese Grenze.
          </p>
        </div>
      </div>

      <div>
        <Label className="mb-2 block">Arbeitszeiten</Label>
        <Tabs defaultValue="weekA">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="weekA">Woche A</TabsTrigger>
            <TabsTrigger value="weekB">Woche B</TabsTrigger>
          </TabsList>
          {(['weekA', 'weekB'] as const).map((week) => (
            <TabsContent key={week} value={week} className="space-y-3">
              {daysOfWeek.map((day) => {
                const hours = formData.workingHours[week][day];
                return (
                  <div key={day} className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                    <div className="w-24">
                      <Switch
                        checked={hours.enabled}
                        onCheckedChange={(checked) =>
                          handleWorkingHoursChange(week, day, 'enabled', checked)
                        }
                      />
                      <span className="ml-2 text-sm">{dayLabels[day]}</span>
                    </div>
                    {hours.enabled && (
                      <>
                        <div className="flex-1">
                          <Input
                            type="time"
                            value={hours.start}
                            onChange={(e) =>
                              handleWorkingHoursChange(week, day, 'start', e.target.value)
                            }
                          />
                        </div>
                        <span className="text-gray-500">bis</span>
                        <div className="flex-1">
                          <Input
                            type="time"
                            value={hours.end}
                            onChange={(e) =>
                              handleWorkingHoursChange(week, day, 'end', e.target.value)
                            }
                          />
                        </div>
                      </>
                    )}
                  </div>
                );
              })}
            </TabsContent>
          ))}
        </Tabs>
      </div>

      <div className="flex gap-3 justify-end">
        <Button type="button" variant="outline" onClick={onClose}>
          Abbrechen
        </Button>
        <Button type="submit">
          {employee ? 'Speichern' : 'Hinzufügen'}
        </Button>
      </div>
    </form>
  );
}