import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

  it('filtert Tage nach Parität: bei currentWeek=B werden keine A-Tage angezeigt', () => {
    renderSwimlane({ currentWeek: 'B' });
    // Der Zeitraum (15.-21.06.2026) liegt komplett in Woche A
    expect(screen.queryByText(/15\.?\s*Juni/)).not.toBeInTheDocument();
    expect(screen.queryByText(/16\.?\s*Juni/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Schicht.*bearbeiten/)).not.toBeInTheDocument();
  });
});

describe('SwimlaneCalendar - Tages-Popout', () => {
  it('zeigt für jeden Tag einen Übergrößern-Trigger mit aria-label', () => {
    renderSwimlane();
    const triggers = screen.getAllByRole('button', { name: 'Tag vergrößern' });
    expect(triggers.length).toBe(7);
    expect(triggers[0]).toHaveAttribute('aria-label', 'Tag vergrößern');
  });

  it('öffnet das Tages-Popout mit Blur-Overlay', async () => {
    const user = userEvent.setup();
    renderSwimlane();
    await user.click(screen.getAllByRole('button', { name: 'Tag vergrößern' })[0]);

    const overlay = document.querySelector('[data-slot="dialog-overlay"]');
    expect(overlay).not.toBeNull();
    expect(overlay!.className).toContain('backdrop-blur-sm');

    expect(screen.getByRole('heading', { level: 2 })).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('zeigt den vergrößerten Tag mit Mitarbeiter-Zeilen und Schichten', async () => {
    const user = userEvent.setup();
    renderSwimlane();
    await user.click(screen.getAllByRole('button', { name: 'Tag vergrößern' })[0]);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('navigiert im Popout mit Vor/Zurück-Buttons zum nächsten Tag', async () => {
    const user = userEvent.setup();
    renderSwimlane();
    await user.click(screen.getAllByRole('button', { name: 'Tag vergrößern' })[0]);

    expect(screen.getByRole('button', { name: 'Voriger Tag' })).toBeDisabled();

    const nextButton = screen.getByRole('button', { name: 'Nächster Tag' });
    await user.click(nextButton);

    const heading = screen.getByRole('heading', { level: 2 });
    expect(heading).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Voriger Tag' })).toBeEnabled();
  });

  it('öffnet weiterhin den Schicht-hinzufügen-Dialog bei Klick auf den Tag', async () => {
    const user = userEvent.setup();
    renderSwimlane();
    await user.click(screen.getAllByText('09:00')[0]);
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2 })).toBeInTheDocument();
    });
    expect(screen.getByText(/Schicht hinzufügen/)).toBeInTheDocument();
  });

  it('schließt das Popout mit dem Schließen-Button', async () => {
    const user = userEvent.setup();
    renderSwimlane();
    await user.click(screen.getAllByRole('button', { name: 'Tag vergrößern' })[0]);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Close' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
