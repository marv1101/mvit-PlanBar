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
  updateMaxRequirement: (templateIndex: number, roleId: string, count: number) => void;
  maximizeStaffing: boolean;
  setMaximizeStaffing: (v: boolean) => void;
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
  updateMaxRequirement,
  maximizeStaffing,
  setMaximizeStaffing,
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
        updateMaxRequirement={updateMaxRequirement}
        submitting={submitting}
      />

      <div className="flex items-center gap-2 mt-2">
        <input
          type="checkbox"
          id="maximizeStaffing"
          checked={maximizeStaffing}
          onChange={(e) => setMaximizeStaffing(e.target.checked)}
          disabled={submitting}
          className="rounded"
        />
        <Label htmlFor="maximizeStaffing" className="text-sm cursor-pointer">
          Alle Mitarbeiter maximal einplanen
        </Label>
      </div>

      <div>
        <Label htmlFor="titoWeekType">Planungsumfang</Label>
        <select
          id="titoWeekType"
          value={titoWeekType}
          onChange={(e) => setTitoWeekType(e.target.value)}
          disabled={submitting}
          className="w-full border rounded-md px-3 py-2"
        >
          <option value="">Beide Wochentypen (A & B)</option>
          <option value="A">Nur Woche A</option>
          <option value="B">Nur Woche B</option>
        </select>
      </div>
    </div>
  );
}
