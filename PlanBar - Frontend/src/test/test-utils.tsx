import React from 'react';
import { render, screen } from '@testing-library/react';
import { DndProvider } from 'react-dnd';
import { TouchBackend } from 'react-dnd-touch-backend';
import { AppContext } from '../app/context/AppContext';
import { Employee, Schedule, WeekType } from '../types';

export const mockEmployees: Employee[] = [
  {
    id: '1',
    name: 'Max Müller',
    email: 'max@example.com',
    roles: ['Koch'],
    workingHours: {
      weekA: {
        monday: { start: '08:00', end: '18:00', enabled: true },
        tuesday: { start: '08:00', end: '18:00', enabled: true },
        wednesday: { start: '08:00', end: '18:00', enabled: true },
        thursday: { start: '08:00', end: '18:00', enabled: true },
        friday: { start: '08:00', end: '18:00', enabled: true },
        saturday: { start: '08:00', end: '18:00', enabled: false },
        sunday: { start: '08:00', end: '18:00', enabled: false },
      },
      weekB: {
        monday: { start: '08:00', end: '18:00', enabled: true },
        tuesday: { start: '08:00', end: '18:00', enabled: true },
        wednesday: { start: '08:00', end: '18:00', enabled: true },
        thursday: { start: '08:00', end: '18:00', enabled: true },
        friday: { start: '08:00', end: '18:00', enabled: true },
        saturday: { start: '08:00', end: '18:00', enabled: false },
        sunday: { start: '08:00', end: '18:00', enabled: false },
      },
    },
    breakTime: { start: '12:00', end: '13:00', duration: 60 },
    color: '#3b82f6',
  },
  {
    id: '2',
    name: 'Anna Schmidt',
    email: 'anna@example.com',
    roles: ['Service'],
    workingHours: {
      weekA: {
        monday: { start: '09:00', end: '17:00', enabled: true },
        tuesday: { start: '09:00', end: '17:00', enabled: true },
        wednesday: { start: '09:00', end: '17:00', enabled: true },
        thursday: { start: '09:00', end: '17:00', enabled: true },
        friday: { start: '09:00', end: '17:00', enabled: true },
        saturday: { start: '09:00', end: '17:00', enabled: false },
        sunday: { start: '09:00', end: '17:00', enabled: false },
      },
      weekB: {
        monday: { start: '09:00', end: '17:00', enabled: true },
        tuesday: { start: '09:00', end: '17:00', enabled: true },
        wednesday: { start: '09:00', end: '17:00', enabled: true },
        thursday: { start: '09:00', end: '17:00', enabled: true },
        friday: { start: '09:00', end: '17:00', enabled: true },
        saturday: { start: '09:00', end: '17:00', enabled: false },
        sunday: { start: '09:00', end: '17:00', enabled: false },
      },
    },
    breakTime: { start: '12:00', end: '12:30', duration: 30 },
    color: '#ef4444',
  },
];

export const mockSchedule: Schedule = {
  id: 'sched-1',
  name: 'Test Woche',
  status: 'draft',
  startDate: '2026-06-15',
  endDate: '2026-06-21',
  shifts: [
    {
      id: 'shift-1',
      employeeId: '1',
      date: '2026-06-15',
      week: 'A',
      startTime: '08:00',
      endTime: '18:00',
      breakStart: '12:00',
      breakEnd: '13:00',
    },
    {
      id: 'shift-2',
      employeeId: '2',
      date: '2026-06-15',
      week: 'A',
      startTime: '09:00',
      endTime: '17:00',
      breakStart: '12:00',
      breakEnd: '12:30',
    },
    {
      id: 'shift-3',
      employeeId: '1',
      date: '2026-06-16',
      week: 'A',
      startTime: '10:00',
      endTime: '16:00',
    },
  ],
};

const mockAppContext = {
  employees: mockEmployees,
  addEmployee: vi.fn(),
  updateEmployee: vi.fn(),
  deleteEmployee: vi.fn(),
  requests: [],
  addRequest: vi.fn(),
  updateRequest: vi.fn(),
  deleteRequest: vi.fn(),
  schedules: [mockSchedule],
  addSchedule: vi.fn(),
  updateSchedule: vi.fn(),
  deleteSchedule: vi.fn(),
  currentSchedule: null,
  setCurrentSchedule: vi.fn(),
  currentWeek: 'A' as WeekType,
  setCurrentWeek: vi.fn(),
  roles: [],
  addRole: vi.fn(),
  updateRole: vi.fn(),
  deleteRole: vi.fn(),
  loading: false,
  refresh: vi.fn(),
};

export function TestWrapper({ children }: { children: React.ReactNode }) {
  return (
    <AppContext.Provider value={mockAppContext as any}>
      <DndProvider backend={TouchBackend} options={{ enableMouseEvents: true }}>
        {children}
      </DndProvider>
    </AppContext.Provider>
  );
}
