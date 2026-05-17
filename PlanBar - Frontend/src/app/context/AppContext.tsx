import React, { createContext, useContext, useState, ReactNode } from 'react';
import { Employee, Request, Schedule, WeekType, Role } from '../types';

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
}

const AppContext = createContext<AppContextType | undefined>(undefined);

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

const initialEmployees: Employee[] = [
  {
    id: '1',
    name: 'Dr. Maria Schmidt',
    email: 'maria.schmidt@apotheke.de',
    roles: ['apotheker'],
    workingHours: defaultWorkingHours,
    breakTime: { start: '12:00', end: '13:00', duration: 60 },
    color: '#3b82f6',
  },
  {
    id: '2',
    name: 'Thomas Müller',
    email: 'thomas.mueller@apotheke.de',
    roles: ['pta'],
    workingHours: {
      ...defaultWorkingHours,
      weekA: {
        ...defaultWorkingHours.weekA,
        friday: { start: '08:00', end: '14:00', enabled: true },
        saturday: { start: '08:00', end: '14:00', enabled: false },
      },
    },
    breakTime: { start: '12:30', end: '13:00', duration: 30 },
    color: '#10b981',
  },
  {
    id: '3',
    name: 'Anna Weber',
    email: 'anna.weber@apotheke.de',
    roles: ['pka'],
    workingHours: defaultWorkingHours,
    breakTime: { start: '13:00', end: '14:00', duration: 60 },
    color: '#f59e0b',
  },
];

const initialRoles: Role[] = [
  { id: 'apotheker', name: 'Apotheker', color: '#3b82f6' },
  { id: 'pta', name: 'PTA', color: '#10b981' },
  { id: 'pka', name: 'PKA', color: '#f59e0b' },
  { id: 'reinigung', name: 'Reinigung', color: '#8b5cf6' },
];

export function AppProvider({ children }: { children: ReactNode }) {
  const [employees, setEmployees] = useState<Employee[]>(initialEmployees);
  const [requests, setRequests] = useState<Request[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [currentSchedule, setCurrentSchedule] = useState<Schedule | null>(null);
  const [currentWeek, setCurrentWeek] = useState<WeekType>('A');
  const [roles, setRoles] = useState<Role[]>(initialRoles);

  const addEmployee = (employee: Employee) => {
    setEmployees([...employees, employee]);
  };

  const updateEmployee = (id: string, updatedEmployee: Employee) => {
    setEmployees(employees.map(emp => emp.id === id ? updatedEmployee : emp));
  };

  const deleteEmployee = (id: string) => {
    setEmployees(employees.filter(emp => emp.id !== id));
    setRequests(requests.filter(req => req.employeeId !== id));
  };

  const addRequest = (request: Request) => {
    setRequests([...requests, request]);
  };

  const updateRequest = (id: string, updatedRequest: Request) => {
    setRequests(requests.map(req => req.id === id ? updatedRequest : req));
  };

  const deleteRequest = (id: string) => {
    setRequests(requests.filter(req => req.id !== id));
  };

  const addSchedule = (schedule: Schedule) => {
    setSchedules([...schedules, schedule]);
  };

  const updateSchedule = (id: string, updatedSchedule: Schedule) => {
    setSchedules(schedules.map(sch => sch.id === id ? updatedSchedule : sch));
  };

  const deleteSchedule = (id: string) => {
    setSchedules(schedules.filter(sch => sch.id !== id));
    if (currentSchedule?.id === id) {
      setCurrentSchedule(null);
    }
  };

  const addRole = (role: Role) => {
    setRoles([...roles, role]);
  };

  const updateRole = (id: string, updatedRole: Role) => {
    setRoles(roles.map(r => r.id === id ? updatedRole : r));
  };

  const deleteRole = (id: string) => {
    setRoles(roles.filter(r => r.id !== id));
  };

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