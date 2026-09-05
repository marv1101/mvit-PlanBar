import { render, screen } from '@testing-library/react'
import { FairnessMeter } from '../FairnessMeter'
import { describe, it, expect } from 'vitest'
import type { Employee, Role, EmployeeFairnessEntry } from '../../types'

const baseEmployee: Employee = {
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
}

const roles: Role[] = [
  { id: 'koch', name: 'Koch', color: '#3b82f6' },
]

const fairnessEntry: EmployeeFairnessEntry = {
  currentBalanceHours: 5,
  scheduledHours: 40,
  contractHours: 40,
  targetHours: 20,
  projectedBalance: 2.5,
  fairnessDeviation: 0,
}

describe('FairnessMeter', () => {
  it('gibt null zurück wenn employeeFairness undefiniert ist', () => {
    const { container } = render(
      <FairnessMeter employees={[]} roles={[]} employeeFairness={undefined} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('gibt null zurück wenn employeeFairness leer ist', () => {
    const { container } = render(
      <FairnessMeter employees={[]} roles={[]} employeeFairness={{}} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('rendert Chart mit Mitarbeiterdaten', () => {
    const employeeFairness: Record<string, EmployeeFairnessEntry> = {
      '1': fairnessEntry,
    }
    render(
      <FairnessMeter
        employees={[baseEmployee]}
        roles={roles}
        employeeFairness={employeeFairness}
      />,
    )

    expect(screen.getByText('Fairness-Meter')).toBeInTheDocument()
    expect(screen.getAllByText(/Geplante Stunden/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Vertragsstunden/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/Abweichung/)).toBeInTheDocument()
  })

  it('rendert auch mit emp_XXX IDs', () => {
    const employeeFairness: Record<string, EmployeeFairnessEntry> = {
      'emp_001': fairnessEntry,
    }
    const { container } = render(
      <FairnessMeter
        employees={[baseEmployee]}
        roles={roles}
        employeeFairness={employeeFairness}
      />,
    )

    expect(screen.getByText('Fairness-Meter')).toBeInTheDocument()
    expect(container.querySelector('.recharts-responsive-container')).toBeInTheDocument()
  })

  it('zeigt mehrere Mitarbeiter im Chart an', () => {
    const emp2: Employee = { ...baseEmployee, id: '2', name: 'Anna Schmidt' }
    const employeeFairness: Record<string, EmployeeFairnessEntry> = {
      '1': fairnessEntry,
      '2': { ...fairnessEntry, scheduledHours: 35, currentBalanceHours: -2 },
    }

    render(
      <FairnessMeter
        employees={[baseEmployee, emp2]}
        roles={roles}
        employeeFairness={employeeFairness}
      />,
    )

    expect(screen.getByText('Fairness-Meter')).toBeInTheDocument()
    expect(screen.getAllByText(/pro Mitarbeiter/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/Abweichung/)).toBeInTheDocument()
  })
})
