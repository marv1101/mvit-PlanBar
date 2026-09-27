import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthContext } from '../../context/AuthContext';
import { AppContext } from '../../context/AppContext';
import { TeamContext } from '../../context/TeamContext';
import { EmployeeView } from '../EmployeeView';
import { mockSchedule, mockEmployees, mockAuthContext, mockAppContext } from '../../../test/test-utils';

const completedSchedule = { ...mockSchedule, status: 'completed' as const };

const appContext = {
  ...mockAppContext,
  schedules: [completedSchedule],
};

function renderView() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <AuthContext.Provider value={mockAuthContext as any}>
          <AppContext.Provider value={appContext as any}>
            <TeamContext.Provider value={{ teams: [], selectedTeamId: null, setSelectedTeamId: vi.fn(), loading: false, refresh: vi.fn().mockResolvedValue(undefined) }}>
              <EmployeeView />
            </TeamContext.Provider>
          </AppContext.Provider>
        </AuthContext.Provider>
      </QueryClientProvider>
    </MemoryRouter>
  );
}

describe('EmployeeView - Tages-Popout', () => {
  it('zeigt nach Auswahl Mitarbeiter+Plan Vergrößern-Trigger für jeden Kalendertag', async () => {
    const user = userEvent.setup();
    renderView();

    await user.selectOptions(screen.getByLabelText('Mitarbeiter'), '1');
    await user.selectOptions(screen.getByLabelText('Schichtplan'), '1');

    await screen.findByText(/Kalenderansicht - Woche A/);
    const triggers = await screen.findAllByRole('button', { name: 'Tag vergrößern' });
    expect(triggers.length).toBe(7);
  });

  it('öffnet das Popout mit der vergrößerten Tagesansicht einer Schicht', async () => {
    const user = userEvent.setup();
    renderView();

    await user.selectOptions(screen.getByLabelText('Mitarbeiter'), '1');
    await user.selectOptions(screen.getByLabelText('Schichtplan'), '1');

    const triggers = await screen.findAllByRole('button', { name: 'Tag vergrößern' });
    await user.click(triggers[0]);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    const dialog = within(screen.getByRole('dialog'));
    expect(dialog.getAllByText(/08:00 - 18:00/).length).toBe(1);
    expect(dialog.getAllByText(/Pause: 12:00 - 13:00/).length).toBe(1);
  });

  it('navigiert mit Vor/Zurück zwischen den Tagen', async () => {
    const user = userEvent.setup();
    renderView();

    await user.selectOptions(screen.getByLabelText('Mitarbeiter'), '1');
    await user.selectOptions(screen.getByLabelText('Schichtplan'), '1');

    const triggers = await screen.findAllByRole('button', { name: 'Tag vergrößern' });
    await user.click(triggers[0]);

    expect(screen.getByRole('button', { name: 'Voriger Tag' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Nächster Tag' }));

    expect(screen.getByText(/Keine Schichten an diesem Tag/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Voriger Tag' })).toBeEnabled();
  });

  it('öffnet für einen Tag ohne Schicht den Leere-Hinweis', async () => {
    const user = userEvent.setup();
    renderView();

    await user.selectOptions(screen.getByLabelText('Mitarbeiter'), '1');
    await user.selectOptions(screen.getByLabelText('Schichtplan'), '1');

    const triggers = await screen.findAllByRole('button', { name: 'Tag vergrößern' });
    await user.click(triggers[1]);

    expect(screen.getByText(/Keine Schichten an diesem Tag/)).toBeInTheDocument();
  });
});
