import { Label } from '../../ui/label';
import { Calendar, X } from 'lucide-react';
import type { ShiftTemplateEntry } from '../../../types';

interface ShiftTemplateEditorProps {
  shiftTemplates: ShiftTemplateEntry[];
  roles: unknown[];
  addShiftTemplate: () => void;
  removeShiftTemplate: (index: number) => void;
  updateShiftTemplate: (index: number, field: string, value: string | boolean | Record<string, number>) => void;
  updateRequirement: (templateIndex: number, roleId: string, count: number) => void;
  updateMaxRequirement: (templateIndex: number, roleId: string, count: number) => void;
  submitting: boolean;
}

export function ShiftTemplateEditor({
  shiftTemplates,
  roles,
  addShiftTemplate,
  removeShiftTemplate,
  updateShiftTemplate,
  updateRequirement,
  updateMaxRequirement,
  submitting,
}: ShiftTemplateEditorProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label>Schicht-Templates</Label>
        <button
          type="button"
          onClick={addShiftTemplate}
          disabled={submitting}
          className="flex items-center gap-1 px-3 py-1 border rounded-md hover:bg-gray-50 disabled:bg-gray-100"
        >
          <Calendar className="h-4 w-4 mr-1" />
          Schicht hinzufügen
        </button>
      </div>

      {shiftTemplates.length === 0 && (
        <p className="text-sm text-gray-500">
          Keine Schichten definiert. Klicken Sie auf &quot;Schicht hinzufügen&quot;, um eine zu erstellen.
        </p>
      )}

      <div className="space-y-3">
        {shiftTemplates.map((st, index) => (
          <div key={st.id} className="border rounded-lg p-4 space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              <div>
                <Label className="text-xs">Name</Label>
                <input
                  value={st.name}
                  onChange={(e) => updateShiftTemplate(index, 'name', e.target.value)}
                  placeholder="z.B. Frühschicht"
                  disabled={submitting}
                  className="w-full border rounded-md px-2 py-1 text-sm"
                />
              </div>
              <div>
                <Label className="text-xs">Startzeit</Label>
                <input
                  type="time"
                  value={st.startTime}
                  onChange={(e) => updateShiftTemplate(index, 'startTime', e.target.value)}
                  disabled={submitting}
                  className="w-full border rounded-md px-2 py-1 text-sm"
                />
              </div>
              <div>
                <Label className="text-xs">Endzeit</Label>
                <input
                  type="time"
                  value={st.endTime}
                  onChange={(e) => updateShiftTemplate(index, 'endTime', e.target.value)}
                  disabled={submitting}
                  className="w-full border rounded-md px-2 py-1 text-sm"
                />
              </div>
              <div className="flex items-end">
                <button
                  type="button"
                  onClick={() => removeShiftTemplate(index)}
                  disabled={submitting}
                  className="p-1 rounded-md hover:bg-red-50 disabled:bg-gray-100"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div>
              <Label className="text-xs">Rollen-Anforderungen pro Tag (Min - Max)</Label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-1">
                {(roles as { id: string; name: string; color: string }[]).map(role => (
                  <div key={role.id} className="flex items-center gap-2">
                    <div
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: role.color }}
                    />
                    <span className="text-xs truncate">{role.name}</span>
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        min="0"
                        max="999"
                        value={st.requirements[role.id] || 0}
                        onChange={(e) => updateRequirement(index, role.id, Math.min(999, Math.max(0, parseInt(e.target.value) || 0)))}
                        className="w-16 h-8 text-xs border rounded-md px-1"
                        disabled={submitting}
                        title="Min. Belegung"
                      />
                      <span className="text-xs text-gray-400">-</span>
                      <input
                        type="number"
                        min="0"
                        max="999"
                        value={st.maxRequirements?.[role.id] || ''}
                        onChange={(e) => {
                          const val = Math.min(999, Math.max(0, parseInt(e.target.value) || 0));
                          updateMaxRequirement(index, role.id, val);
                        }}
                        className="w-16 h-8 text-xs border rounded-md px-1"
                        disabled={submitting}
                        placeholder="max"
                        title="Max. Belegung (optional)"
                      />
                    </div>
                  </div>
                ))}
                {roles.length === 0 && (
                  <p className="text-xs text-gray-500 col-span-full">
                    Keine Rollen vorhanden. Erstellen Sie zuerst Rollen.
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-4 pt-1">
              <Label className="text-xs">Wochenendarbeit</Label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={st.saturday || false}
                  onChange={(e) => updateShiftTemplate(index, 'saturday', e.target.checked)}
                  disabled={submitting}
                  className="w-4 h-4 rounded border-gray-300"
                />
                <span className="text-xs">Samstag</span>
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={st.sunday || false}
                  onChange={(e) => updateShiftTemplate(index, 'sunday', e.target.checked)}
                  disabled={submitting}
                  className="w-4 h-4 rounded border-gray-300"
                />
                <span className="text-xs">Sonntag</span>
              </label>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
