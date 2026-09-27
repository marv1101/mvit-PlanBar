import { eachDayOfInterval, format, parseISO } from 'date-fns';
import { de } from 'date-fns/locale';
import { isWeekend } from 'date-fns';
import { KioskBoardDTO, KioskShiftDTO } from '../../services/kioskService';
import { useIsMobile } from '../ui/use-mobile';
import { cn } from '../ui/utils';

interface KioskBoardProps {
  board: KioskBoardDTO;
  lastUpdated?: number;
  today?: string;
}

export function KioskBoard({ board, lastUpdated, today = format(new Date(), 'yyyy-MM-dd') }: KioskBoardProps) {
  const isMobile = useIsMobile();
  const days = eachDayOfInterval({
    start: parseISO(board.window_start),
    end: parseISO(board.window_end),
  });

  const updatedLabel =
    lastUpdated !== undefined ? (
      <p className="text-base text-slate-400">
        Zuletzt aktualisiert: {format(new Date(lastUpdated), 'HH:mm')}
      </p>
    ) : null;

  if (board.shifts.length === 0) {
    return (
      <div data-testid="kiosk-board" className="py-16 text-center">
        <p className="text-2xl font-medium text-slate-300">
          Kein Dienstplan für den Zeitraum
        </p>
        <p className="text-slate-500 mt-2">
          {format(parseISO(board.window_start), 'dd.MM.yyyy')} –{' '}
          {format(parseISO(board.window_end), 'dd.MM.yyyy')}
        </p>
        {updatedLabel}
      </div>
    );
  }

  return (
    <div data-testid="kiosk-board" className="text-lg">
      {updatedLabel}
      {isMobile ? (
        <MobileBoard board={board} days={days} />
      ) : (
        <DesktopBoard board={board} days={days} today={today} />
      )}
    </div>
  );
}

function isoOf(date: Date): string {
  return format(date, 'yyyy-MM-dd');
}

function DesktopBoard({
  board,
  days,
  today,
}: {
  board: KioskBoardDTO;
  days: Date[];
  today: string;
}) {
  const gridTemplate = `minmax(200px, 260px) repeat(${days.length}, minmax(0, 1fr))`;

  return (
    <div className="space-y-4">
      <div
        style={{ display: 'grid', gridTemplateColumns: gridTemplate }}
        className="rounded-lg bg-slate-900 border border-slate-800 overflow-x-auto"
      >
        <div className="px-3 py-3 font-semibold text-slate-300 sticky left-0">Mitarbeiter</div>
        {days.map((day) => (
          <DayHeader key={isoOf(day)} date={day} today={today} />
        ))}
        {board.employees.map((employee) => (
          <EmployeeRow
            key={employee.id}
            employeeId={employee.id}
            name={employee.name}
            color={employee.color}
            shifts={board.shifts.filter((s) => s.employee_id === employee.id)}
            days={days}
            today={today}
            gridTemplate={gridTemplate}
          />
        ))}
      </div>
    </div>
  );
}

function DayHeader({ date, today }: { date: Date; today: string }) {
  const iso = isoOf(date);
  const isToday = iso === today;
  return (
    <div
      data-testid={`kiosk-col-${iso}`}
      aria-current={isToday ? 'date' : undefined}
      data-weekend={isWeekend(date) ? 'true' : 'false'}
      className={cn(
        'px-2 py-3 text-center font-semibold border-b border-slate-800',
        isWeekend(date) && 'bg-slate-900/80 text-slate-400',
        isToday && 'bg-blue-600/30 text-blue-200',
      )}
    >
      <span className="block text-base md:text-lg">
        {format(date, 'EEE', { locale: de })}
      </span>
      <span className="block text-lg md:text-xl">{format(date, 'dd.MM.')}</span>
    </div>
  );
}

function EmployeeRow({
  employeeId,
  name,
  color,
  shifts,
  days,
  today,
  gridTemplate,
}: {
  employeeId: number;
  name: string;
  color: string | null;
  shifts: KioskShiftDTO[];
  days: Date[];
  today: string;
  gridTemplate: string;
}) {
  return (
    <div
      data-testid={`kiosk-row-${employeeId}`}
      style={{ display: 'grid', gridTemplateColumns: gridTemplate }}
      className="border-t border-slate-800"
    >
      <div className="flex items-center gap-3 px-3 py-3 font-semibold text-xl">
        <span
          data-testid={`kiosk-dot-${employeeId}`}
          className="inline-block h-4 w-4 md:h-5 md:w-5 rounded-full shrink-0"
          style={{ backgroundColor: color ?? '#9ca3af' }}
        />
        <span className="truncate" title={name}>{name}</span>
      </div>
      {days.map((day) => {
        const iso = isoOf(day);
        const dayShifts = shifts.filter((s) => s.date === iso);
        return (
          <div
            key={iso}
            data-testid={`kiosk-cell-${employeeId}-${iso}`}
            data-weekend={isWeekend(day) ? 'true' : 'false'}
            className={cn(
              'p-1 space-y-1 min-h-20',
              isWeekend(day) && 'bg-slate-900/40',
              iso === today && 'bg-blue-950/30',
            )}
          >
            {dayShifts.map((shift, idx) => (
              <ShiftBlock key={idx} shift={shift} />
            ))}
          </div>
        );
      })}
    </div>
  );
}

function ShiftBlock({ shift }: { shift: KioskShiftDTO }) {
  const time = `${shift.start_time.slice(0, 5)}–${shift.end_time.slice(0, 5)}`;
  return (
    <div className="rounded-md bg-blue-600/80 text-white px-2 py-2 text-base md:text-lg leading-snug">
      {shift.label && <div className="font-bold">{shift.label}</div>}
      <div className="font-medium">{time}</div>
      {shift.break_start && shift.break_end && (
        <div className="text-xs md:text-sm opacity-80">
          Pause {shift.break_start.slice(0, 5)}–{shift.break_end.slice(0, 5)}
        </div>
      )}
    </div>
  );
}

function MobileBoard({ board, days }: { board: KioskBoardDTO; days: Date[] }) {
  return (
    <div className="space-y-4">
      {days.map((day) => {
        const iso = isoOf(day);
        const dayShifts = board.shifts.filter((s) => s.date === iso);
        if (dayShifts.length === 0) return null;
        return (
          <section key={iso} className="rounded-lg bg-slate-900 border border-slate-800 p-4">
            <h2 className="text-xl font-semibold mb-3">
              {format(day, 'EEEE, dd.MM.', { locale: de })}
            </h2>
            <ul className="space-y-3">
              {dayShifts.map((shift, idx) => {
                const employee = board.employees.find((e) => e.id === shift.employee_id);
                return (
                  <li key={idx} className="flex items-start gap-3">
                    <span
                      data-testid={`kiosk-dot-${shift.employee_id}`}
                      className="inline-block h-4 w-4 rounded-full shrink-0 mt-1"
                      style={{ backgroundColor: employee?.color ?? '#9ca3af' }}
                    />
                    <div>
                      <p className="font-semibold text-lg">
                        {employee?.name ?? `Mitarbeiter #${shift.employee_id}`}
                      </p>
                      <ShiftBlock shift={shift} />
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
