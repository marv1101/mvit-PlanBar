import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DayDetailDialog } from './DayDetailDialog';
import { TestWrapper } from '../../../../test/test-utils';

const defaultProps = {
  open: true,
  onOpenChange: vi.fn(),
  title: 'Montag, 15.06.2026',
  showNavigation: true,
  hasPrev: true,
  hasNext: true,
  onPrev: vi.fn(),
  onNext: vi.fn(),
};

describe('DayDetailDialog', () => {
  it('nutzt im fullScreen-Modus den gesamten Bildschirm', () => {
    render(
      <TestWrapper>
        <DayDetailDialog {...defaultProps} fullScreen>
          <div>Inhalt</div>
        </DayDetailDialog>
      </TestWrapper>
    );
    const content = document.querySelector('[data-slot="dialog-content"]');
    expect(content).not.toBeNull();
    expect(content!.className).toContain('w-screen');
    expect(content!.className).toContain('sm:max-w-none');
    expect(content!.className).toContain('rounded-none');
  });

  it('dehnt den Inhaltsbereich vertikal über die gesamte Dialoghöhe', () => {
    render(
      <TestWrapper>
        <DayDetailDialog {...defaultProps} fullScreen>
          <div data-testid="content-inhalt" className="h-full">Inhalt</div>
        </DayDetailDialog>
      </TestWrapper>
    );
    const content = document.querySelector('[data-slot="dialog-content"]') as HTMLElement;
    const wrapper = content.querySelector('[data-testid="content-inhalt"]')!.parentElement!;
    expect(wrapper.className).toContain('h-full');
    expect(content.className).toContain('grid-rows-[auto_1fr]');
  });

  it('nutzt im Standardmodus near-Fullscreen-Maße ohne sm:max-w-lg-Limit', () => {
    render(
      <TestWrapper>
        <DayDetailDialog {...defaultProps}>
          <div>Inhalt</div>
        </DayDetailDialog>
      </TestWrapper>
    );
    const content = document.querySelector('[data-slot="dialog-content"]');
    expect(content!.className).not.toContain('sm:max-w-lg');
    expect(content!.className).toContain('sm:max-w-none');
  });

  it('nutzt im Standardmodus near-Fullscreen-Maße', () => {
    render(
      <TestWrapper>
        <DayDetailDialog {...defaultProps}>
          <div>Inhalt</div>
        </DayDetailDialog>
      </TestWrapper>
    );
    const content = document.querySelector('[data-slot="dialog-content"]');
    expect(content!.className).toContain('w-[95vw]');
    expect(content!.className).toContain('h-[92vh]');
  });
  it('rendert Titel und Inhalt im Portal (document.body)', () => {
    const { baseElement } = render(
      <TestWrapper>
        <DayDetailDialog {...defaultProps}>
          <div>Testinhalt</div>
        </DayDetailDialog>
      </TestWrapper>
    );
    expect(screen.getByText('Testinhalt')).toBeInTheDocument();
    expect(baseElement.ownerDocument.body).toContainElement(screen.getByText('Testinhalt'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('hat ein BlurOverlay (backdrop-blur)', () => {
    render(
      <TestWrapper>
        <DayDetailDialog {...defaultProps}>
          <div>Inhalt</div>
        </DayDetailDialog>
      </TestWrapper>
    );
    const overlay = document.querySelector('[data-slot="dialog-overlay"]');
    expect(overlay).not.toBeNull();
    expect(overlay!.className).toContain('backdrop-blur-sm');
    expect(overlay!.className).toContain('bg-black/60');
  });

  it('zeigt Vor- und Zurück-Buttons', () => {
    render(
      <TestWrapper>
        <DayDetailDialog {...defaultProps}>
          <div>Inhalt</div>
        </DayDetailDialog>
      </TestWrapper>
    );
    expect(screen.getByRole('button', { name: 'Voriger Tag' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Nächster Tag' })).toBeInTheDocument();
  });

  it('ruft onPrev/onNext bei Klick auf die Navigations-Buttons auf', async () => {
    const user = userEvent.setup();
    const onPrev = vi.fn();
    const onNext = vi.fn();
    render(
      <TestWrapper>
        <DayDetailDialog {...defaultProps} onPrev={onPrev} onNext={onNext}>
          <div>Inhalt</div>
        </DayDetailDialog>
      </TestWrapper>
    );
    await user.click(screen.getByRole('button', { name: 'Voriger Tag' }));
    await user.click(screen.getByRole('button', { name: 'Nächster Tag' }));
    expect(onPrev).toHaveBeenCalledTimes(1);
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('navigiert mit Pfeiltasten (ArrowLeft/ArrowRight)', () => {
    const onPrev = vi.fn();
    const onNext = vi.fn();
    render(
      <TestWrapper>
        <DayDetailDialog {...defaultProps} onPrev={onPrev} onNext={onNext}>
          <div>Inhalt</div>
        </DayDetailDialog>
      </TestWrapper>
    );
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft' }));
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight' }));
    expect(onPrev).toHaveBeenCalledTimes(1);
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('deaktiviert Zurück am Anfang und Vor am Ende', () => {
    render(
      <TestWrapper>
        <DayDetailDialog {...defaultProps} hasPrev={false} hasNext={false}>
          <div>Inhalt</div>
        </DayDetailDialog>
      </TestWrapper>
    );
    expect(screen.getByRole('button', { name: 'Voriger Tag' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Nächster Tag' })).toBeDisabled();
  });

  it('versteckt Navigation, wenn showNavigation=false', () => {
    render(
      <TestWrapper>
        <DayDetailDialog {...defaultProps} showNavigation={false}>
          <div>Inhalt</div>
        </DayDetailDialog>
      </TestWrapper>
    );
    expect(screen.queryByRole('button', { name: 'Voriger Tag' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Nächster Tag' })).not.toBeInTheDocument();
  });

  it('rendert nichts, wenn open=false', () => {
    render(
      <TestWrapper>
        <DayDetailDialog {...defaultProps} open={false}>
          <div>Inhalt</div>
        </DayDetailDialog>
      </TestWrapper>
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('zeigt Titel mit Vollbild-Maßen (near-fullscreen)', () => {
    render(
      <TestWrapper>
        <DayDetailDialog {...defaultProps}>
          <div>Inhalt</div>
        </DayDetailDialog>
      </TestWrapper>
    );
    expect(screen.getByText('Montag, 15.06.2026')).toBeInTheDocument();
  });
});
