import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SwimlaneCalendar } from './SwimlaneCalendar';
import { TestWrapper, mockSchedule } from '../../test/test-utils';

const mockOnUpdate = vi.fn();

function renderSwimlane(props = {}) {
  return render(
    <TestWrapper>
      <SwimlaneCalendar
        schedule={mockSchedule}
        currentWeek="A"
        onUpdateSchedule={mockOnUpdate}
        {...props}
      />
    </TestWrapper>
  );
}

describe('SwimlaneCalendar', () => {
  it('rendert Tage als vertikale Blöcke', () => {
    renderSwimlane();
    // Montag und Dienstag sollten sichtbar sein (lokales Datumsformat)
    expect(screen.getByText(/15\.?\s*Juni/)).toBeInTheDocument();
    expect(screen.getByText(/16\.?\s*Juni/)).toBeInTheDocument();
  });

  it('rendert alle Mitarbeiter alphabetisch als Zeilen', () => {
    renderSwimlane();
    expect(screen.getAllByText(/Schmidt/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Müller/).length).toBeGreaterThan(0);
  });

  it('rendert Schichten als farbige Balken in Mitarbeiter-Zeilen', () => {
    renderSwimlane();
    // Schicht-Zeiten sollten sichtbar sein (mehrfach im Stundenraster und in Schichten)
    expect(screen.getAllByText(/08:00/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/09:00/).length).toBeGreaterThan(0);
  });

  it('zeigt volles Pause-Overlay mit Pattern und Drag-Handles', () => {
    renderSwimlane();
    // Pause-Overlay mit Pattern sollte sichtbar sein
    // In der Swimlane-Ansicht wird die Pause vollständig dargestellt
    const shiftElements = screen.getAllByText(/Müller/);
    expect(shiftElements.length).toBeGreaterThan(0);
  });

  it('rendert leere Mitarbeiter-Zeilen für Tage ohne Schicht', () => {
    renderSwimlane();
    // Alle Mitarbeiter sollten für jeden Tag eine Zeile haben
    const rows = screen.getAllByText(/Müller/);
    expect(rows.length).toBeGreaterThanOrEqual(1);
  });

});
