import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { Employee, Request, Schedule, WeekType, Role } from '../types';
import { getWeekType } from '../lib/week';
import { toast } from 'sonner';
import * as employeeService from '../services/employeeService';
import * as roleService from '../services/roleService';
import * as requestService from '../services/requestService';
import * as scheduleService from '../services/scheduleService';
import {
  employeeFromResponse,
  employeeToCreate,
  roleFromResponse,
  roleToCreate,
  requestFromResponse,
  requestToCreate,
  scheduleFromResponse,
} from '../lib/mappers';

interface AppContextType {
  employees: Employee[];
  addEmployee: (employee: Employee) => void;
  updateEmployee: (id: string, employee: Employee) => void;
  deleteEmployee: (id: string) => void;

  requests: Request[];
  addRequest: (request: Request) => void;
  updateRequest: (id: string, request: Request) => void;
  deleteRequest: (id: string) => void;

  schedules: Schedule[];
  addSchedule: (schedule: Schedule) => void;
  updateSchedule: (id: string, schedule: Schedule) => void;
  deleteSchedule: (id: string) => void;
  currentSchedule: Schedule | null;
  setCurrentSchedule: (schedule: Schedule | null) => void;

  currentWeek: WeekType;
  setCurrentWeek: (week: WeekType) => void;

  roles: Role[];
  addRole: (role: Role) => void;
  updateRole: (id: string, role: Role) => void;
  deleteRole: (id: string) => void;

  loading: boolean;
  refresh: () => Promise<void>;
}

export const AppContext = createContext<AppContextType | undefined>(undefined);

async function loadAll() {
  const [empRes, roleRes, reqRes, schedRes] = await Promise.all([
    employeeService.getEmployees(),
    roleService.getRoles(),
    requestService.getShiftWishes(),
    scheduleService.getSchedules(),
  ]);
  return {
    employees: empRes.map(employeeFromResponse),
    roles: roleRes.map(roleFromResponse),
    requests: reqRes.map(requestFromResponse),
    schedules: schedRes.map(scheduleFromResponse),
  };
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [requests, setRequests] = useState<Request[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [currentSchedule, setCurrentSchedule] = useState<Schedule | null>(null);
  const [currentWeek, setCurrentWeek] = useState<WeekType>(() => getWeekType(new Date()));
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await loadAll();
      setEmployees(data.employees);
      setRoles(data.roles);
      setRequests(data.requests);
      setSchedules(data.schedules);
    } catch {
      toast.error('Fehler beim Laden der Daten');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const addEmployee = useCallback((employee: Employee) => {
    const dto = employeeToCreate(employee);
    employeeService.createEmployee(dto)
      .then(res => {
        setEmployees(prev => [...prev, employeeFromResponse(res)]);
        toast.success('Mitarbeiter erstellt');
      })
      .catch(() => toast.error('Fehler beim Erstellen des Mitarbeiters'));
  }, []);

  const updateEmployee = useCallback((id: string, employee: Employee) => {
    const dto = employeeToCreate(employee);
    employeeService.updateEmployee(Number(id), dto)
      .then(res => {
        setEmployees(prev => prev.map(e => e.id === id ? employeeFromResponse(res) : e));
        toast.success('Mitarbeiter aktualisiert');
      })
      .catch(() => toast.error('Fehler beim Aktualisieren des Mitarbeiters'));
  }, []);

  const deleteEmployee = useCallback((id: string) => {
    employeeService.deleteEmployee(Number(id))
      .then(() => {
        setEmployees(prev => prev.filter(e => e.id !== id));
        setRequests(prev => prev.filter(r => r.employeeId !== id));
        toast.success('Mitarbeiter gelöscht');
      })
      .catch(() => toast.error('Fehler beim Löschen des Mitarbeiters'));
  }, []);

  const addRequest = useCallback((request: Request) => {
    const dto = requestToCreate(request);
    requestService.createShiftWish(dto)
      .then(res => {
        setRequests(prev => [...prev, requestFromResponse(res)]);
        toast.success('Wunsch erstellt');
      })
      .catch(() => toast.error('Fehler beim Erstellen des Wunsches'));
  }, []);

  const updateRequest = useCallback((id: string, request: Request) => {
    const dto = requestToCreate(request);
    requestService.updateShiftWish(Number(id), dto)
      .then(() => {
        setRequests(prev => prev.map(r => r.id === id ? request : r));
        toast.success('Wunsch aktualisiert');
      })
      .catch(() => toast.error('Fehler beim Aktualisieren des Wunsches'));
  }, []);

  const deleteRequest = useCallback((id: string) => {
    requestService.deleteShiftWish(Number(id))
      .then(() => {
        setRequests(prev => prev.filter(r => r.id !== id));
        toast.success('Wunsch gelöscht');
      })
      .catch(() => toast.error('Fehler beim Löschen des Wunsches'));
  }, []);

  const addSchedule = useCallback((schedule: Schedule) => {
    setSchedules(prev => [...prev, schedule]);
  }, []);

  const updateSchedule = useCallback((id: string, schedule: Schedule) => {
    scheduleService.updateSchedule(Number(id), { name: schedule.name, week_type: undefined, status: schedule.status })
      .then(() => {
        setSchedules(prev => prev.map(s => s.id === id ? schedule : s));
        toast.success('Schichtplan aktualisiert');
      })
      .catch(() => toast.error('Fehler beim Aktualisieren des Schichtplans'));
  }, []);

  const deleteSchedule = useCallback((id: string) => {
    scheduleService.deleteSchedule(Number(id))
      .then(() => {
        setSchedules(prev => prev.filter(s => s.id !== id));
        if (currentSchedule?.id === id) {
          setCurrentSchedule(null);
        }
        toast.success('Schichtplan gelöscht');
      })
      .catch(() => toast.error('Fehler beim Löschen des Schichtplans'));
  }, [currentSchedule]);

  const addRole = useCallback((role: Role) => {
    const dto = roleToCreate(role);
    roleService.createRole(dto)
      .then(res => {
        setRoles(prev => [...prev, roleFromResponse(res)]);
        toast.success('Rolle erstellt');
      })
      .catch(() => toast.error('Fehler beim Erstellen der Rolle'));
  }, []);

  const updateRole = useCallback((id: string, role: Role) => {
    const dto = roleToCreate(role);
    roleService.updateRole(Number(id), dto)
      .then(() => {
        setRoles(prev => prev.map(r => r.id === id ? role : r));
        toast.success('Rolle aktualisiert');
      })
      .catch(() => toast.error('Fehler beim Aktualisieren der Rolle'));
  }, []);

  const deleteRole = useCallback((id: string) => {
    roleService.deleteRole(Number(id))
      .then(() => {
        setRoles(prev => prev.filter(r => r.id !== id));
        toast.success('Rolle gelöscht');
      })
      .catch(() => toast.error('Fehler beim Löschen der Rolle'));
  }, []);

  return (
    <AppContext.Provider
      value={{
        employees,
        addEmployee,
        updateEmployee,
        deleteEmployee,
        requests,
        addRequest,
        updateRequest,
        deleteRequest,
        schedules,
        addSchedule,
        updateSchedule,
        deleteSchedule,
        currentSchedule,
        setCurrentSchedule,
        currentWeek,
        setCurrentWeek,
        roles,
        addRole,
        updateRole,
        deleteRole,
        loading,
        refresh,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
