import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as scheduleService from '../services/scheduleService';
import { scheduleFromResponse } from '../lib/mappers';
import { toast } from 'sonner';

const QUERY_KEY = ['schedules'];

export function useSchedules() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const res = await scheduleService.getSchedules();
      return res.items.map(scheduleFromResponse);
    },
  });
}

export function useSchedule(id: number | null) {
  return useQuery({
    queryKey: [...QUERY_KEY, id],
    queryFn: async () => {
      const res = await scheduleService.getSchedule(id!);
      return scheduleFromResponse(res);
    },
    enabled: id !== null,
  });
}

export function useUpdateSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: { name?: string; week_type?: string; status?: string } }) =>
      scheduleService.updateSchedule(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success('Schichtplan aktualisiert');
    },
    onError: (error: unknown) => {
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        toast.error('Die Daten wurden inzwischen geändert. Bitte Seite neu laden.');
        queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      } else {
        toast.error('Fehler beim Aktualisieren des Schichtplans');
      }
    },
  });
}

export function useDeleteSchedule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => scheduleService.deleteSchedule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success('Schichtplan gelöscht');
    },
    onError: () => {
      toast.error('Fehler beim Löschen des Schichtplans');
    },
  });
}
