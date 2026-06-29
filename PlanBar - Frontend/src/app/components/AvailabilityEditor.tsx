import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CalendarDays, Loader2, Save } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { toast } from 'sonner';
import { getMyAvailability, updateMyAvailability } from '../services/selfService';
import type { AvailabilityEntryDTO } from '../services/selfService';

const dayNames = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'];

const defaultEntries: AvailabilityEntryDTO[] = dayNames.map((_, i) => ({
  day_of_week: i,
  available: true,
  note: '',
}));

export function AvailabilityEditor() {
  const queryClient = useQueryClient();

  const { data: serverData, isLoading } = useQuery({
    queryKey: ['my-availability'],
    queryFn: getMyAvailability,
  });

  const [entries, setEntries] = React.useState<AvailabilityEntryDTO[]>(defaultEntries);

  React.useEffect(() => {
    if (serverData && serverData.length > 0) {
      const merged = defaultEntries.map(def => {
        const found = serverData.find(s => s.day_of_week === def.day_of_week);
        return found
          ? { day_of_week: found.day_of_week, available: found.available, note: found.note || '' }
          : def;
      });
      setEntries(merged);
    }
  }, [serverData]);

  const updateMutation = useMutation({
    mutationFn: updateMyAvailability,
    onSuccess: () => {
      toast.success('Verfügbarkeit gespeichert');
      queryClient.invalidateQueries({ queryKey: ['my-availability'] });
    },
    onError: () => toast.error('Fehler beim Speichern'),
  });

  const toggleDay = (dayOfWeek: number) => {
    setEntries(prev => prev.map(e =>
      e.day_of_week === dayOfWeek ? { ...e, available: !e.available } : e
    ));
  };

  const updateNote = (dayOfWeek: number, note: string) => {
    setEntries(prev => prev.map(e =>
      e.day_of_week === dayOfWeek ? { ...e, note } : e
    ));
  };

  const handleSave = () => {
    updateMutation.mutate({ entries });
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Loader2 className="h-8 w-8 mx-auto text-blue-600 mb-4 animate-spin" />
          <p className="text-gray-600">Lade Verfügbarkeit...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CalendarDays className="h-5 w-5" />
          Meine Verfügbarkeit
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          {entries.map(entry => (
            <div key={entry.day_of_week} className="flex items-center gap-4 p-3 border rounded-lg">
              <Switch
                checked={entry.available}
                onCheckedChange={() => toggleDay(entry.day_of_week)}
              />
              <div className="flex-1">
                <Label className={`font-medium ${!entry.available ? 'text-red-600' : ''}`}>
                  {dayNames[entry.day_of_week]}
                </Label>
                <Input
                  placeholder="Notiz (optional)"
                  value={entry.note || ''}
                  onChange={e => updateNote(entry.day_of_week, e.target.value)}
                  className="mt-1 text-sm"
                />
              </div>
              <span className={`text-sm font-medium ${entry.available ? 'text-green-600' : 'text-red-600'}`}>
                {entry.available ? 'Verfügbar' : 'Nicht verfügbar'}
              </span>
            </div>
          ))}
        </div>

        <Button onClick={handleSave} disabled={updateMutation.isPending} className="w-full">
          {updateMutation.isPending ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          Verfügbarkeit speichern
        </Button>
      </CardContent>
    </Card>
  );
}
