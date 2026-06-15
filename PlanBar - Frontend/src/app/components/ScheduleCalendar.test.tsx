import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ScheduleCalendar } from './ScheduleCalendar';
import { TestWrapper, mockSchedule } from '../../test/test-utils';

function renderCalendar(props = {}) {
  return render(
    <TestWrapper>
      <ScheduleCalendar
        shifts={mockSchedule.shifts}
        startDate={mockSchedule.startDate}
        endDate={mockSchedule.endDate}
        currentWeek="A"
        {...props}
      />
    </TestWrapper>
  );
}

describe('ScheduleCalendar - Swimlane-Ansicht (Standard)', () => {
  it('zeigt die Swimlane-Ansicht als Standard mit Mitarbeiter-Zeilen', () => {
    renderCalendar();
    expect(screen.getAllByText(/Max Müller/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Anna Schmidt/).length).toBeGreaterThan(0);
  });

  it('zeigt den View-Toggle-Button', () => {
    renderCalendar();
    expect(screen.getByRole('button', { name: /Timeline-Ansicht/i })).toBeInTheDocument();
  });

  it('zeigt Schicht-Zeiten in der Swimlane-Ansicht', () => {
    renderCalendar();
    expect(screen.getAllByText(/08:00/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/18:00/).length).toBeGreaterThan(0);
  });

  it('zeigt Tages-Header in der Swimlane-Ansicht', () => {
    renderCalendar();
    expect(screen.getByText(/15\.\s*Juni/i)).toBeInTheDocument();
    expect(screen.getByText(/16\.\s*Juni/i)).toBeInTheDocument();
  });

  it('zeigt Legende mit Mitarbeiter-Farben', () => {
    renderCalendar();
    expect(screen.getByText(/Legende/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Max Müller/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText(/Anna Schmidt/).length).toBeGreaterThanOrEqual(2);
  });
});

describe('ScheduleCalendar - View-Toggle', () => {
  it('wechselt zur Timeline-Ansicht bei Klick auf Toggle', async () => {
    const user = userEvent.setup();
    renderCalendar();

    const toggleButton = screen.getByRole('button', { name: /Timeline-Ansicht/i });
    await user.click(toggleButton);

    expect(screen.getByRole('button', { name: /Mitarbeiter-Ansicht/i })).toBeInTheDocument();
  });

  it('zeigt in der Timeline-Ansicht das Raster mit Tagen', async () => {
    const user = userEvent.setup();
    renderCalendar();

    const toggleButton = screen.getByRole('button', { name: /Timeline-Ansicht/i });
    await user.click(toggleButton);

    expect(screen.getByText(/15\.\s*Juni/i)).toBeInTheDocument();
    expect(screen.getByText(/16\.\s*Juni/i)).toBeInTheDocument();
  });

  it('behält den View-Mode nach Re-Render', async () => {
    const user = userEvent.setup();
    const { rerender } = renderCalendar();

    const toggleButton = screen.getByRole('button', { name: /Timeline-Ansicht/i });
    await user.click(toggleButton);

    rerender(
      <TestWrapper>
        <ScheduleCalendar
          shifts={mockSchedule.shifts}
          startDate={mockSchedule.startDate}
          endDate={mockSchedule.endDate}
          currentWeek="A"
        />
      </TestWrapper>
    );

    expect(screen.getByRole('button', { name: /Mitarbeiter-Ansicht/i })).toBeInTheDocument();
  });
});

describe('ScheduleCalendar - Week-Filter', () => {
  it('zeigt nur Schichten der aktuellen Woche in Swimlane-Ansicht', () => {
    renderCalendar({ currentWeek: 'B' });
    expect(screen.queryByText(/08:00/)).not.toBeInTheDocument();
  });

  it('zeigt nur Schichten der aktuellen Woche in Timeline-Ansicht', async () => {
    const user = userEvent.setup();
    renderCalendar({ currentWeek: 'B' });

    const toggleButton = screen.getByRole('button', { name: /Timeline-Ansicht/i });
    await user.click(toggleButton);

    expect(screen.queryByText(/08:00/)).not.toBeInTheDocument();
  });
});
