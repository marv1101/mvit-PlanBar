import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, it, expect } from 'vitest';
import { PrivacyPolicy } from '../PrivacyPolicy';

function renderPrivacyPolicy() {
  return render(
    <MemoryRouter>
      <PrivacyPolicy />
    </MemoryRouter>,
  );
}

describe('PrivacyPolicy', () => {
  it('rendert die Datenschutzerklärung Überschrift', () => {
    renderPrivacyPolicy();
    expect(screen.getByRole('heading', { name: 'Datenschutzerklärung' })).toBeInTheDocument();
  });

  it('rendert den Verantwortlichen (Art. 4 Nr. 7 DSGVO)', () => {
    renderPrivacyPolicy();
    expect(screen.getByRole('heading', { name: /Verantwortlicher \(Art\. 4 Nr\. 7 DSGVO\)/ })).toBeInTheDocument();
    expect(screen.getAllByText('MVIT PlanBar').length).toBeGreaterThan(0);
  });

  it('rendert die Betroffenenrechte (Art. 15–22 DSGVO)', () => {
    renderPrivacyPolicy();
    expect(screen.getByRole('heading', { name: /Ihre Betroffenenrechte/ })).toBeInTheDocument();
    expect(screen.getByText(/Auskunftsrecht/)).toBeInTheDocument();
    expect(screen.getByText(/Recht auf Berichtigung/)).toBeInTheDocument();
    expect(screen.getByText(/Recht auf Löschung/)).toBeInTheDocument();
    expect(screen.getByText(/Recht auf Datenübertragbarkeit/)).toBeInTheDocument();
    expect(screen.getByText(/Widerspruchsrecht/)).toBeInTheDocument();
  });

  it('rendert den Hinweis auf Beschwerderecht (Art. 77 DSGVO)', () => {
    renderPrivacyPolicy();
    expect(screen.getByRole('heading', { name: /Beschwerderecht/ })).toBeInTheDocument();
  });

  it('rendert die Kontaktmöglichkeit für Datenschutzfragen', () => {
    renderPrivacyPolicy();
    expect(screen.getByRole('heading', { name: 'Kontakt bei Datenschutzfragen' })).toBeInTheDocument();
    expect(screen.getByText('Datenschutzbeauftragter')).toBeInTheDocument();
  });

  it('rendert die Rechtsgrundlagen (Art. 6 Abs. 1 DSGVO)', () => {
    renderPrivacyPolicy();
    expect(screen.getByRole('heading', { name: /Rechtsgrundlagen/ })).toBeInTheDocument();
    expect(screen.getByText(/Vertragserfüllung/)).toBeInTheDocument();
    expect(screen.getByText(/Rechtliche Verpflichtung/)).toBeInTheDocument();
    expect(screen.getByText(/Berechtigtes Interesse/)).toBeInTheDocument();
    expect(screen.getAllByText(/Einwilligung/).length).toBeGreaterThan(0);
  });

  it('rendert die Speicherdauer-Angaben', () => {
    renderPrivacyPolicy();
    const headings = screen.getAllByRole('heading', { level: 4 });
    expect(headings.map(h => h.textContent)).toContain('Speicherdauer');
  });

  it('rendert den Hinweis zu Drittländern', () => {
    renderPrivacyPolicy();
    expect(screen.getByRole('heading', { name: /Datenübermittlung in Drittländer/ })).toBeInTheDocument();
  });
});
