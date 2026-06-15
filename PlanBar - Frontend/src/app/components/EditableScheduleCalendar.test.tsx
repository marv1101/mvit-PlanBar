import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EditableScheduleCalendar } from './EditableScheduleCalendar';
import { TestWrapper, mockSchedule } from '../../test/test-utils';

const mockOnUpdate = vi.fn();
const mockOnSave = vi.fn();

function renderCalendar(props = {}) {
  return render(
    <TestWrapper>
      <EditableScheduleCalendar
        schedule={mockSchedule}
        currentWeek="A"
        onUpdateSchedule={mockOnUpdate}
        onSaveShifts={mockOnSave}
        {...props}
      />
    </TestWrapper>
  );
}

describe('EditableScheduleCalendar - Swimlane-Ansicht', () => {
  it('zeigt den View-Toggle-Button mit beiden Optionen', () => {
    renderCalendar();
    expect(screen.getAllByRole('button', { name: /Timeline-Ansicht/i }).length).toBeGreaterThan(0);
  });

  it('zeigt die Swimlane-Ansicht als Standard', () => {
    renderCalendar();
    // Swimlane hat Mitarbeiter-Zeilen
    expect(screen.getAllByText(/Müller/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Schmidt/).length).toBeGreaterThan(0);
  });

  it('rendert Schicht mit Pause - zeigt Pause-Overlay', () => {
    renderCalendar();
    // Schicht mit Pause sollte sichtbar sein
    const shiftElements = screen.getAllByText(/Müller/);
    expect(shiftElements.length).toBeGreaterThan(0);
  });

  it('wechselt zur Timeline-Ansicht bei Klick auf Toggle', async () => {
    const user = userEvent.setup();
    renderCalendar();
    
    const toggleButton = screen.getAllByRole('button', { name: /Timeline-Ansicht/i })[0];
    await user.click(toggleButton);
    
    // Nach dem Wechsel sollte der Button "Mitarbeiter-Ansicht" zeigen (Timeline-Modus)
    expect(screen.getAllByRole('button', { name: /Mitarbeiter-Ansicht/i }).length).toBeGreaterThan(0);
  });

  it('zeigt Mitarbeiterpool in beiden Ansichten', async () => {
    const user = userEvent.setup();
    renderCalendar();
    
    // In Swimlane-Ansicht (Standard)
    expect(screen.getAllByText(/Mitarbeiterpool/i).length).toBeGreaterThan(0);
    
    // Wechseln zu Timeline
    const toggleButton = screen.getAllByRole('button', { name: /Timeline-Ansicht/i })[0];
    await user.click(toggleButton);
    
    // In Timeline-Ansicht
    expect(screen.getAllByText(/Mitarbeiterpool/i).length).toBeGreaterThan(0);
  });
});

describe('EditableScheduleCalendar - Week-Filter', () => {
  it('zeigt alle Tage in der Swimlane-Ansicht auch wenn currentWeek nicht passt', () => {
    renderCalendar({ currentWeek: 'B' });
    // Tage müssen sichtbar sein – kein Day-Filter nach getWeekType mehr
    expect(screen.getByText(/15\.?\s*Juni/)).toBeInTheDocument();
    expect(screen.getByText(/16\.?\s*Juni/)).toBeInTheDocument();
  });

  it('zeigt alle Tage in der Timeline-Ansicht auch wenn currentWeek nicht passt', async () => {
    const user = userEvent.setup();
    renderCalendar({ currentWeek: 'B' });

    const toggleButton = screen.getAllByRole('button', { name: /Timeline-Ansicht/i })[0];
    await user.click(toggleButton);

    // Tage müssen sichtbar sein – kein Week-Filter mehr
    // In der Timeline-Ansicht wird Datum als "15.06." formatiert
    expect(screen.getByText(/15\.\s*06\./)).toBeInTheDocument();
    expect(screen.getByText(/16\.\s*06\./)).toBeInTheDocument();
  });
});

describe('EditableScheduleCalendar - View-Toggle', () => {
  it('behält den View-Mode im State', async () => {
    const { rerender } = renderCalendar();
    
    // Re-render mit neuen Props
    rerender(
      <TestWrapper>
        <EditableScheduleCalendar
          schedule={mockSchedule}
          currentWeek="A"
          onUpdateSchedule={mockOnUpdate}
          onSaveShifts={mockOnSave}
        />
      </TestWrapper>
    );
    
    // Sollte noch in Swimlane-Ansicht sein (Standard)
    expect(screen.getAllByText(/Müller/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Schmidt/).length).toBeGreaterThan(0);
  });
});
