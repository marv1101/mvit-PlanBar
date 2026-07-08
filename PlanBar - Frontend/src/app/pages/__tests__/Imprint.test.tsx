import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, it, expect } from 'vitest';
import { Imprint } from '../Imprint';

function renderImprint() {
  return render(
    <MemoryRouter>
      <Imprint />
    </MemoryRouter>,
  );
}

describe('Imprint', () => {
  it('rendert die Impressum Überschrift', () => {
    renderImprint();
    expect(screen.getByRole('heading', { name: 'Impressum' })).toBeInTheDocument();
  });

  it('rendert den Verantwortlichen (§ 5 TMG)', () => {
    renderImprint();
    expect(screen.getByRole('heading', { name: 'Verantwortlicher' })).toBeInTheDocument();
    expect(screen.getByText('MVIT PlanBar GmbH')).toBeInTheDocument();
  });

  it('rendert die Kontaktdaten (E-Mail)', () => {
    renderImprint();
    expect(screen.getByRole('heading', { name: 'Kontakt' })).toBeInTheDocument();
    expect(screen.getByText(/info@planbar\.example\.com/)).toBeInTheDocument();
  });

  it('rendert den Verantwortlichen für den Inhalt (§ 55 Abs. 2 RStV)', () => {
    renderImprint();
    expect(screen.getByRole('heading', { name: /§ 55 Abs\. 2 RStV/ })).toBeInTheDocument();
  });

  it('rendert den Hinweis zur EU-Streitschlichtung', () => {
    renderImprint();
    expect(screen.getByRole('heading', { name: 'Streitschlichtung' })).toBeInTheDocument();
    expect(screen.getByText(/ec\.europa\.eu\/consumers\/odr/)).toBeInTheDocument();
  });

  it('rendert den Haftungsausschluss', () => {
    renderImprint();
    expect(screen.getByRole('heading', { name: 'Haftungsausschluss' })).toBeInTheDocument();
  });

  it('rendert den DSGVO-Kontakt mit Betroffenenrechten', () => {
    renderImprint();
    expect(screen.getByRole('heading', { name: 'DSGVO-Kontakt' })).toBeInTheDocument();
    expect(screen.getByText(/Auskunftsrecht/)).toBeInTheDocument();
    expect(screen.getByText(/Recht auf Löschung/)).toBeInTheDocument();
    expect(screen.getByText(/Recht auf Datenübertragbarkeit/)).toBeInTheDocument();
  });

  it('rendert den Datenschutzbeauftragten', () => {
    renderImprint();
    expect(screen.getByRole('heading', { name: 'Datenschutzbeauftragter' })).toBeInTheDocument();
  });

  it('rendert den Hinweis auf keine Rechtsberatung', () => {
    renderImprint();
    expect(screen.getByText(/ersetzt keine Rechtsberatung/)).toBeInTheDocument();
  });
});
