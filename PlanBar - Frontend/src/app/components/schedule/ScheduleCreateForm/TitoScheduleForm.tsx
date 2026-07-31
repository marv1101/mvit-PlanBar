import { Label } from '../../ui/label';
import { ShiftTemplateEditor } from './ShiftTemplateEditor';
import type { ShiftTemplateEntry } from '../../../types';

interface TitoScheduleFormProps {
  roles: unknown[];
  shiftTemplates: ShiftTemplateEntry[];
  titoWeekType: string;
  setTitoWeekType: (v: string) => void;
  addShiftTemplate: () => void;
  removeShiftTemplate: (index: number) => void;
  updateShiftTemplate: (index: number, field: string, value: string | Record<string, number>) => void;
  updateRequirement: (templateIndex: number, roleId: string, count: number) => void;
  scheduleName: string;
  setScheduleName: (v: string) => void;
  startDate: string;
  setStartDate: (v: string) => void;
  endDate: string;
  setEndDate: (v: string) => void;
  creating: boolean;
  submitting: boolean;
}

export function TitoScheduleForm({
  roles,
  shiftTemplates,
  titoWeekType,
  setTitoWeekType,
  addShiftTemplate,
  removeShiftTemplate,
  updateShiftTemplate,
  updateRequirement,
  scheduleName,
  setScheduleName,
  startDate,
  setStartDate,
  endDate,
  setEndDate,
  creating,
  submitting,
}: TitoScheduleFormProps) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="scheduleName">Plan-Name</Label>
        <input
          id="scheduleName"
          value={scheduleName}
          onChange={(e) => setScheduleName(e.target.value)}
          placeholder="z.B. April 2026"
          disabled={submitting}
          maxLength={100}
          className="w-full border rounded-md px-3 py-2"
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label htmlFor="startDate">Startdatum</Label>
          <input
            id="startDate"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            disabled={submitting}
            className="w-full border rounded-md px-3 py-2"
          />
        </div>
        <div>
          <Label htmlFor="endDate">Enddatum</Label>
          <input
            id="endDate"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            disabled={submitting}
            className="w-full border rounded-md px-3 py-2"
          />
        </div>
      </div>

      <ShiftTemplateEditor
        shiftTemplates={shiftTemplates}
        roles={roles}
        addShiftTemplate={addShiftTemplate}
        removeShiftTemplate={removeShiftTemplate}
        updateShiftTemplate={updateShiftTemplate}
        updateRequirement={updateRequirement}
        submitting={submitting}
      />

      <div>
        <Label htmlFor="titoWeekType">Wochen-Typ</Label>
        <select
          id="titoWeekType"
          value={titoWeekType}
          onChange={(e) => setTitoWeekType(e.target.value)}
          disabled={submitting}
          className="w-full border rounded-md px-3 py-2"
        >
          <option value="A">Nur Woche A</option>
          <option value="B">Nur Woche B</option>
          <option value="">Beide (A & B)</option>
        </select>
      </div>

      <button
        type="button"
        disabled={submitting || creating}
        className="w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
      >
        {submitting ? 'Wird erstellt...' : 'Schichtplan erstellen & an TiTO senden'}
      </button>
    </div>
  );
}
