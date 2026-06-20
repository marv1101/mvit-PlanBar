import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChangePasswordDialog } from '../ChangePasswordDialog'
import { renderWithAuth } from '../../../test/test-utils'
import { describe, it, expect, vi } from 'vitest'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

describe('ChangePasswordDialog', () => {
  it('rendert Titel und Beschreibung', () => {
    renderWithAuth(<ChangePasswordDialog />)

    expect(screen.getByRole('heading', { name: 'Passwort ändern' })).toBeInTheDocument()
    expect(
      screen.getByText('Sie müssen Ihr Passwort nach der ersten Anmeldung ändern.'),
    ).toBeInTheDocument()
  })

  it('rendert Submit-Button', () => {
    renderWithAuth(<ChangePasswordDialog />)

    expect(screen.getByRole('button', { name: 'Passwort ändern' })).toBeInTheDocument()
  })

  it('rendert alle Passwortfelder', () => {
    renderWithAuth(<ChangePasswordDialog />)

    expect(screen.getByLabelText('Aktuelles Passwort')).toBeInTheDocument()
    expect(screen.getByLabelText('Neues Passwort')).toBeInTheDocument()
    expect(screen.getByLabelText('Neues Passwort bestätigen')).toBeInTheDocument()
  })

  it('zeigt Fehler bei nicht übereinstimmenden neuen Passwörtern', async () => {
    const user = userEvent.setup()
    renderWithAuth(<ChangePasswordDialog />)

    await user.type(screen.getByLabelText('Aktuelles Passwort'), 'altes123')
    await user.type(screen.getByLabelText('Neues Passwort'), 'neues123')
    await user.type(screen.getByLabelText('Neues Passwort bestätigen'), 'anders456')

    await user.click(screen.getByRole('button', { name: 'Passwort ändern' }))

    expect(
      screen.getByText('Die neuen Passwörter stimmen nicht überein'),
    ).toBeInTheDocument()
  })

  it('zeigt Fehler bei zu kurzem neuen Passwort', async () => {
    const user = userEvent.setup()
    renderWithAuth(<ChangePasswordDialog />)

    await user.type(screen.getByLabelText('Aktuelles Passwort'), 'altes123')
    await user.type(screen.getByLabelText('Neues Passwort'), 'kurz')
    await user.type(screen.getByLabelText('Neues Passwort bestätigen'), 'kurz')

    await user.click(screen.getByRole('button', { name: 'Passwort ändern' }))

    expect(
      screen.getByText('Das neue Passwort muss mindestens 8 Zeichen lang sein'),
    ).toBeInTheDocument()
  })

  it('zeigt keinen Fehler bei korrekter Eingabe und gleichen Passwörtern', async () => {
    const user = userEvent.setup()
    renderWithAuth(<ChangePasswordDialog />)

    await user.type(screen.getByLabelText('Aktuelles Passwort'), 'altes123')
    await user.type(screen.getByLabelText('Neues Passwort'), 'neuesPasswort123')
    await user.type(screen.getByLabelText('Neues Passwort bestätigen'), 'neuesPasswort123')

    await user.click(screen.getByRole('button', { name: 'Passwort ändern' }))

    expect(
      screen.queryByText('Die neuen Passwörter stimmen nicht überein'),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByText('Das neue Passwort muss mindestens 8 Zeichen lang sein'),
    ).not.toBeInTheDocument()
  })
})
