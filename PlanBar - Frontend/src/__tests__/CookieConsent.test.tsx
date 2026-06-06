import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CookieConsent } from '../components/CookieConsent'

describe('CookieConsent', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('renders cookie banner when no consent exists', () => {
    render(<CookieConsent />)
    // Check the banner dialog is present
    expect(screen.getByRole('dialog', { name: /cookie/i })).toBeInTheDocument()
    // Check for accept buttons
    expect(screen.getByText(/alle akzeptieren/i)).toBeInTheDocument()
  })

  it('hides cookie banner when consent exists', () => {
    localStorage.setItem('cookie-consent', JSON.stringify({
      necessary: true,
      functional: false,
      analytics: false,
    }))
    render(<CookieConsent />)
    // Banner should not be present
    expect(screen.queryByRole('dialog', { name: /cookie/i })).not.toBeInTheDocument()
  })

  it('accept all sets all cookies', async () => {
    const user = userEvent.setup()
    render(<CookieConsent />)
    
    const acceptAllButton = screen.getByText(/alle akzeptieren/i)
    await user.click(acceptAllButton)
    
    const stored = JSON.parse(localStorage.getItem('cookie-consent') || '{}')
    expect(stored.necessary).toBe(true)
    expect(stored.functional).toBe(true)
    expect(stored.analytics).toBe(true)
  })

  it('accept necessary only sets necessary', async () => {
    const user = userEvent.setup()
    render(<CookieConsent />)
    
    const necessaryButton = screen.getByText(/nur notwendige/i)
    await user.click(necessaryButton)
    
    const stored = JSON.parse(localStorage.getItem('cookie-consent') || '{}')
    expect(stored.necessary).toBe(true)
    expect(stored.functional).toBe(false)
    expect(stored.analytics).toBe(false)
  })

  it('custom consent saves preferences', async () => {
    const user = userEvent.setup()
    render(<CookieConsent />)
    
    // Open settings dialog
    const settingsButton = screen.getByText(/einstellungen/i)
    await user.click(settingsButton)
    
    // Find and click functional switch (uses Switch component, role="switch")
    const functionalSwitch = screen.getByRole('switch', { name: /funktional/i })
    await user.click(functionalSwitch)
    
    // Save
    const saveButton = screen.getByText(/speichern/i)
    await user.click(saveButton)
    
    const stored = JSON.parse(localStorage.getItem('cookie-consent') || '{}')
    expect(stored.necessary).toBe(true)
    expect(stored.functional).toBe(true)
    expect(stored.analytics).toBe(false)
  })

  it('settings link opens dialog', async () => {
    const user = userEvent.setup()
    // Pre-set consent so banner doesn't show
    localStorage.setItem('cookie-consent', JSON.stringify({
      necessary: true,
      functional: false,
      analytics: false,
    }))
    
    render(<CookieConsent />)
    
    const settingsLink = screen.getByTestId('cookie-settings-link')
    await user.click(settingsLink)
    
    // Settings dialog should be open with switches
    expect(screen.getByRole('switch', { name: /funktional/i })).toBeInTheDocument()
    expect(screen.getByRole('switch', { name: /analyse/i })).toBeInTheDocument()
  })
})
