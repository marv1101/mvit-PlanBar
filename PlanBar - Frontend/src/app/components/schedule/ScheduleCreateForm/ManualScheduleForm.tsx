import { Label } from '../../ui/label';
import type { Schedule as ScheduleType } from '../../../types';

interface ManualScheduleFormProps {
  manualName: string;
  setManualName: (v: string) => void;
  manualStartDate: string;
  setManualStartDate: (v: string) => void;
  manualEndDate: string;
  setManualEndDate: (v: string) => void;
  manualWeekType: string;
  setManualWeekType: (v: string) => void;
  manuallyCreatedSchedule: ScheduleType | null;
  submitting: boolean;
  creating: boolean;
  onSubmit: () => void;
  onReset: () => void;
}

export function ManualScheduleForm({
  manualName,
  setManualName,
  manualStartDate,
  setManualStartDate,
  manualEndDate,
  setManualEndDate,
  manualWeekType,
  setManualWeekType,
  manuallyCreatedSchedule,
  submitting,
  creating,
  onSubmit,
  onReset,
}: ManualScheduleFormProps) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="manualName">Plan-Name</Label>
        <input
          id="manualName"
          value={manualName}
          onChange={(e) => setManualName(e.target.value)}
          placeholder="z.B. April 2026"
          disabled={submitting}
          maxLength={100}
          className="w-full border rounded-md px-3 py-2"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label htmlFor="manualStartDate">Startdatum</Label>
          <input
            id="manualStartDate"
            type="date"
            value={manualStartDate}
            onChange={(e) => setManualStartDate(e.target.value)}
            disabled={submitting}
            className="w-full border rounded-md px-3 py-2"
          />
        </div>
        <div>
          <Label htmlFor="manualEndDate">Enddatum</Label>
          <input
            id="manualEndDate"
            type="date"
            value={manualEndDate}
            onChange={(e) => setManualEndDate(e.target.value)}
            disabled={submitting}
            className="w-full border rounded-md px-3 py-2"
          />
        </div>
      </div>

      <div>
        <Label htmlFor="manualWeekType">Planungsumfang</Label>
        <select
          id="manualWeekType"
          value={manualWeekType}
          onChange={(e) => setManualWeekType(e.target.value)}
          disabled={submitting}
          className="w-full border rounded-md px-3 py-2"
        >
          <option value="">Beide Wochentypen (A & B)</option>
          <option value="A">Nur Woche A</option>
          <option value="B">Nur Woche B</option>
        </select>
      </div>

      {!manuallyCreatedSchedule ? (
        <button
          type="button"
          onClick={onSubmit}
          disabled={submitting || creating}
          className="w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
        >
          {submitting ? 'Wird erstellt...' : 'Schichtplan erstellen'}
        </button>
      ) : (
        <div className="p-4 bg-green-50 border border-green-200 rounded-md">
          <p className="text-green-800 font-medium">Schichtplan erfolgreich erstellt!</p>
          <button
            type="button"
            onClick={onReset}
            className="mt-2 text-sm text-blue-600 hover:underline"
          >
            Neuen Plan erstellen
          </button>
        </div>
      )}
    </div>
  );
}
