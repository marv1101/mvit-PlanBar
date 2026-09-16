import { HOURS } from '../shared/CalendarUtils';

const EMPLOYEE_GUTTER_PX = 160;
const DAY_BLOCK_CHROME_HEIGHT_PX = 64;
const MIN_ROW_HEIGHT = 56;
const MIN_HOUR_WIDTH = 96;
const MIN_BAR_HEIGHT = 36;

export interface PopoutSizes {
  hourWidth: number;
  rowHeight: number;
  barHeight: number;
}

/**
 * Berechnet die Größen für die gestreckte Tages-Popout-Ansicht:
 * hourWidth füllt die Dialogbreite, rowHeight füllt die Dialoghöhe vollständig
 * (Zeilen werden gleichmäßig auf die Höhe verteilt und gezoomt),
 * barHeight füllt die Zeile proportional.
 */
export function computePopoutSizes(
  containerWidth: number,
  containerHeight: number,
  employeeCount: number,
): PopoutSizes {
  if (containerWidth <= 0 || containerHeight <= 0 || employeeCount <= 0) {
    return { hourWidth: MIN_HOUR_WIDTH, rowHeight: MIN_ROW_HEIGHT, barHeight: MIN_BAR_HEIGHT };
  }

  const hoursPerRow = HOURS.length;
  const hourWidth = Math.max(MIN_HOUR_WIDTH, Math.floor((containerWidth - EMPLOYEE_GUTTER_PX) / hoursPerRow));

  const rowHeight = Math.max(
    MIN_ROW_HEIGHT,
    Math.floor((containerHeight - DAY_BLOCK_CHROME_HEIGHT_PX) / employeeCount),
  );

  const barHeight = Math.max(MIN_BAR_HEIGHT, rowHeight - 16);

  return { hourWidth, rowHeight, barHeight };
}

/** Schriftgröße des Schichtbalkens skaliert mit der Balkenhöhe. */
export function barTextClass(barHeight: number): string {
  if (barHeight >= 88) return 'text-sm';
  if (barHeight >= 56) return 'text-xs';
  return 'text-[10px]';
}
