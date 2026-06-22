import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import { WishOverlay } from './WishOverlay';
import { Request, Employee } from '../../types';

describe('WishOverlay', () => {
  const mockEmployee: Employee = {
    id: '1',
    name: 'Max Mustermann',
    email: 'max@example.com',
    roles: ['employee'],
    workingHours: {
      weekA: {
        monday: { start: '08:00', end: '17:00', enabled: true },
        tuesday: { start: '08:00', end: '17:00', enabled: true },
        wednesday: { start: '08:00', end: '17:00', enabled: true },
        thursday: { start: '08:00', end: '17:00', enabled: true },
        friday: { start: '08:00', end: '17:00', enabled: true },
        saturday: { start: '08:00', end: '17:00', enabled: false },
        sunday: { start: '08:00', end: '17:00', enabled: false },
      },
      weekB: {
        monday: { start: '08:00', end: '17:00', enabled: true },
        tuesday: { start: '08:00', end: '17:00', enabled: true },
        wednesday: { start: '08:00', end: '17:00', enabled: true },
        thursday: { start: '08:00', end: '17:00', enabled: true },
        friday: { start: '08:00', end: '17:00', enabled: true },
        saturday: { start: '08:00', end: '17:00', enabled: false },
        sunday: { start: '08:00', end: '17:00', enabled: false },
      },
    },
    breakTime: { start: '12:00', end: '13:00', duration: 60 },
    color: '#3b82f6',
  };

  const mockVacationWish: Request = {
    id: '1',
    employeeId: '1',
    date: '2026-06-20',
    week: 'A',
    type: 'urlaubswunsch',
    notes: 'Familienurlaub',
    status: 'approved',
  };

  const mockUnavailableWish: Request = {
    id: '3',
    employeeId: '1',
    date: '2026-06-22',
    week: 'A',
    type: 'nicht-verfügbar',
    notes: 'Arzttermin',
    status: 'approved',
  };

  it('renders vacation wish with correct styling', () => {
    render(
      <WishOverlay wish={mockVacationWish} employee={mockEmployee} />
    );

    expect(screen.getByText('Max Mustermann')).toBeInTheDocument();
    expect(screen.getByText('urlaubswunsch')).toBeInTheDocument();
  });

  it('renders unavailable wish with warning message', () => {
    render(
      <WishOverlay wish={mockUnavailableWish} employee={mockEmployee} />
    );

    expect(screen.getByText('Max Mustermann')).toBeInTheDocument();
    expect(screen.getByText('nicht-verfügbar')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(
      <WishOverlay wish={mockVacationWish} employee={mockEmployee} onClick={handleClick} />
    );

    const element = screen.getByText('Max Mustermann').closest('div')!;
    fireEvent.click(element);
    expect(handleClick).toHaveBeenCalledWith(mockVacationWish);
  });

  it('shows tooltip on hover with notes', async () => {
    render(
      <WishOverlay wish={mockVacationWish} employee={mockEmployee} />
    );

    const element = screen.getByText('Max Mustermann').closest('div')!;
    fireEvent.mouseEnter(element);

    await waitFor(() => {
      expect(screen.getByText('Familienurlaub')).toBeInTheDocument();
    });
  });

  it('shows warning for unavailable wishes on hover', async () => {
    render(
      <WishOverlay wish={mockUnavailableWish} employee={mockEmployee} />
    );

    const element = screen.getByText('Max Mustermann').closest('div')!;
    fireEvent.mouseEnter(element);

    await waitFor(() => {
      expect(screen.getByText(/Keine Schicht zuweisen/)).toBeInTheDocument();
    });
  });
});
