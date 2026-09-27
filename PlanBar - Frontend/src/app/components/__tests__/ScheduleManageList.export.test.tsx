import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ScheduleManageList } from '../schedule/ScheduleManageList';
import * as scheduleService from '../../services/scheduleService';
import type { Schedule, Employee, Role } from '../../types';

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock('../../services/scheduleService', () => ({
  downloadSchedulePdf: vi.fn().mockResolvedValue(undefined),
  downloadScheduleIcal: vi.fn().mockResolvedValue(undefined),
  retrySchedule: vi.fn().mockResolvedValue(undefined),
  replaceAllShifts: vi.fn().mockResolvedValue({}),
}));

vi.mock('../../services/requestService', () => ({
  submitSchedule: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('../ScheduleCalendar', () => ({
  ScheduleCalendar: () => <div data-testid="schedule-calendar" />,
}));

vi.mock('../EditableScheduleCalendar', () => ({
  EditableScheduleCalendar: () => <div data-testid="editable-calendar" />,
}));

vi.mock('../FairnessMeter', () => ({
  FairnessMeter: () => <div data-testid="fairness-meter" />,
}));

vi.mock('./schedule/StatusBadge', () => ({
  StatusBadge: () => <span data-testid="status-badge" />,
}));

vi.mock('./schedule/ArbZgConfirmDialog', () => ({
  ArbZgConfirmDialog: () => <div data-testid="arb-zg-dialog" />,
}));

const employees: Employee[] = [
  {
    id: '1',
    name: 'Max Müller',
    email: 'max@test.de',
    roles: ['koch'],
    workingHours: {
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
    },
    breakTime: { start: '12:00', end: '13:00', duration: 60 },
    color: '#3b82f6',
  },
];

const roles: Role[] = [{ id: 'koch', name: 'Koch', color: '#3b82f6' }];

const schedule: Schedule = {
  id: '42',
  name: 'Testplan',
  status: 'draft',
  startDate: '2026-06-01',
  endDate: '2026-06-07',
  shifts: [
    {
      id: 's1',
      employeeId: '1',
      date: '2026-06-01',
      week: 'A',
      startTime: '08:00',
      endTime: '16:00',
      label: 'Fruehschicht',
    },
  ],
};

const defaultProps = {
  schedules: [schedule],
  loading: false,
  employees,
  roles,
  currentWeek: 'A' as const,
  setCurrentWeek: vi.fn(),
  refresh: vi.fn().mockResolvedValue(undefined),
  submitting: false,
  deleteSchedule: vi.fn(),
  updateSchedule: vi.fn(),
  onWishReview: vi.fn(),
  setCurrentScheduleId: vi.fn(),
  setCurrentScheduleStatus: vi.fn(),
  onCreateTab: vi.fn(),
};

describe('ScheduleManageList Export-Dropdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('rendert einen Export-Button statt drei einzelne Buttons', () => {
    render(<ScheduleManageList {...defaultProps} />);
    expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument();
    // Die alten einzelnen aria-labels dürfen nicht mehr existieren
    expect(screen.queryByRole('button', { name: /pdf exportieren/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /ical exportieren/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /schichtplan exportieren/i })).not.toBeInTheDocument();
  });

   it('öffnet Dropdown mit PDF, iCal und CSV bei Klick', async () => {
    const user = userEvent.setup();
    render(<ScheduleManageList {...defaultProps} />);

    await user.click(screen.getByRole('button', { name: /export/i }));

    expect(screen.getByRole('menuitem', { name: /pdf/i })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /ical/i })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /csv/i })).toBeInTheDocument();
  });

  it('ruft downloadSchedulePdf bei Klick auf PDF', async () => {
    const user = userEvent.setup();
    render(<ScheduleManageList {...defaultProps} />);

    await user.click(screen.getByRole('button', { name: /export/i }));
    await user.click(screen.getByRole('menuitem', { name: /pdf/i }));

    expect(scheduleService.downloadSchedulePdf).toHaveBeenCalledWith(42, 'Testplan');
  });

  it('ruft downloadScheduleIcal bei Klick auf iCal', async () => {
    const user = userEvent.setup();
    render(<ScheduleManageList {...defaultProps} />);

    await user.click(screen.getByRole('button', { name: /export/i }));
    await user.click(screen.getByRole('menuitem', { name: /ical/i }));

    expect(scheduleService.downloadScheduleIcal).toHaveBeenCalledWith(42, 'Testplan');
  });
});
