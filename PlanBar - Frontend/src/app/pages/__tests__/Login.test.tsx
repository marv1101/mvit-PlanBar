import React from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { AuthContext } from '../../context/AuthContext'
import { Login } from '../Login'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const baseAuthValue = {
  user: null,
  login: vi.fn(),
  logout: vi.fn(),
  isLoading: false,
  mustChangePassword: false,
  changePassword: vi.fn(),
}

function renderLogin(authValue = baseAuthValue) {
  return render(
    <MemoryRouter>
      <AuthContext.Provider value={authValue as any}>
        <Login />
      </AuthContext.Provider>
    </MemoryRouter>,
  )
}

describe('Login', () => {
  it('rendert E-Mail- und Passwort-Felder', () => {
    renderLogin()
    expect(screen.getByLabelText('E-Mail')).toBeInTheDocument()
    expect(screen.getByLabelText('Passwort')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Anmelden' })).toBeInTheDocument()
  })

  it('zeigt Fehler bei fehlgeschlagenem Login', async () => {
    const login = vi.fn().mockResolvedValue({ success: false, mustChangePassword: false })
    renderLogin({ ...baseAuthValue, login })

    const user = userEvent.setup()
    await user.type(screen.getByLabelText('E-Mail'), 'test@test.com')
    await user.type(screen.getByLabelText('Passwort'), 'falsch')
    await user.click(screen.getByRole('button', { name: 'Anmelden' }))

    expect(await screen.findByText('Ungültige E-Mail oder Passwort')).toBeInTheDocument()
  })

  it('deaktiviert Inputs während des Ladens', async () => {
    const login = vi.fn().mockReturnValue(new Promise<never>(() => {}))
    renderLogin({ ...baseAuthValue, login })

    const user = userEvent.setup()
    await user.type(screen.getByLabelText('E-Mail'), 'test@test.com')
    await user.type(screen.getByLabelText('Passwort'), 'pass')
    await user.click(screen.getByRole('button', { name: 'Anmelden' }))

    expect(screen.getByLabelText('E-Mail')).toBeDisabled()
    expect(screen.getByLabelText('Passwort')).toBeDisabled()
  })
})
