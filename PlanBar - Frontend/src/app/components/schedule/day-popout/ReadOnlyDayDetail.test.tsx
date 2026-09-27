import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ReadOnlyDayDetail } from './ReadOnlyDayDetail';
import { mockEmployees, mockSchedule } from '../../../../test/test-utils';

describe('ReadOnlyDayDetail', () => {
  it('zeigt Schichten des Mitarbeiters mit Uhrzeit und Pause groß', () => {
    render(
      <ReadOnlyDayDetail
        date={new Date('2026-06-15T00:00:00Z')}
        shifts={mockSchedule.shifts.filter(s => s.employeeId === '1')}
        employees={mockEmployees}
      />
    );
    expect(screen.getByText(/08:00/)).toBeInTheDocument();
    expect(screen.getByText(/18:00/)).toBeInTheDocument();
    expect(screen.getByText(/12:00/)).toBeInTheDocument();
    expect(screen.getByText('Backoffice')).toBeInTheDocument();
  });

  it('zeigt Hinweis, wenn keine Schichten geplant sind', () => {
    render(
      <ReadOnlyDayDetail
        date={new Date('2026-06-16T00:00:00Z')}
        shifts={[]}
        employees={mockEmployees}
      />
    );
    expect(screen.getByText(/Keine Schichten an diesem Tag/)).toBeInTheDocument();
  });

  it('zeigt den Wochentag als Untertitel', () => {
    render(
      <ReadOnlyDayDetail
        date={new Date('2026-06-15T00:00:00Z')}
        shifts={[]}
        employees={mockEmployees}
      />
    );
    expect(screen.getByText(/Montag/)).toBeInTheDocument();
  });
});
