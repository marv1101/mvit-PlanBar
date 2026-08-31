import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Request, RequestType } from '../types';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Textarea } from './ui/textarea';
import { weekTypeOfDateStr } from '../lib/week';

interface RequestFormProps {
  request: Request | null;
  onClose: () => void;
  currentEmployeeId?: string;
  isAdmin?: boolean;
  defaultType?: RequestType;
}

export function RequestForm({ request, onClose, currentEmployeeId, isAdmin = true, defaultType }: RequestFormProps) {
  const { addRequest, updateRequest, employees } = useApp();

  // Use currentEmployeeId for non-admin users, otherwise use first employee or request employee
  const defaultEmployeeId = isAdmin
    ? (employees[0]?.id || '')
    : (currentEmployeeId || '');

  const [formData, setFormData] = useState<Request>(
    request || {
      id: Date.now().toString(),
      employeeId: defaultEmployeeId,
      date: new Date().toISOString().split('T')[0],
      week: weekTypeOfDateStr(new Date().toISOString().split('T')[0]),
      type: defaultType || 'urlaubswunsch',
      notes: '',
    }
  );

  const handleDateChange = (date: string) => {
    setFormData({ ...formData, date, week: weekTypeOfDateStr(date) });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (request) {
      updateRequest(request.id, formData);
    } else {
      addRequest(formData);
    }
    onClose();
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="employee">Mitarbeiter</Label>
        {isAdmin ? (
          <Select
            value={formData.employeeId}
            onValueChange={(value) => setFormData({ ...formData, employeeId: value })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {employees.map((emp) => (
                <SelectItem key={emp.id} value={emp.id}>
                  {emp.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <Input
            value={employees.find(e => e.id === formData.employeeId)?.name || ''}
            disabled
            className="bg-gray-100"
          />
        )}
      </div>

      <div>
        <Label htmlFor="date">Datum</Label>
        <Input
          id="date"
          type="date"
          value={formData.date}
          onChange={(e) => handleDateChange(e.target.value)}
          required
        />
      </div>

      <div>
        <Label htmlFor="type">Art des Wunsches</Label>
        <Select
          value={formData.type}
          onValueChange={(value: RequestType) => setFormData({ ...formData, type: value })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="urlaubswunsch">Urlaubswunsch</SelectItem>
            <SelectItem value="bevorzugt">Bevorzugt</SelectItem>
            <SelectItem value="nicht-verfügbar">Nicht verfügbar</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label htmlFor="notes">Notizen (optional)</Label>
        <Textarea
          id="notes"
          value={formData.notes}
          onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
          placeholder="Zusätzliche Informationen..."
        />
      </div>

      <div className="flex gap-3 justify-end">
        <Button type="button" variant="outline" onClick={onClose}>
          Abbrechen
        </Button>
        <Button type="submit">
          {request ? 'Speichern' : 'Hinzufügen'}
        </Button>
      </div>
    </form>
  );
}
