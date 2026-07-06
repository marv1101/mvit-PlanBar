import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as requestService from '../services/requestService';
import { requestFromResponse, requestToCreate } from '../lib/mappers';
import { Request } from '../types';
import { toast } from 'sonner';

const QUERY_KEY = ['shiftWishes'];

export function useShiftWishes() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const res = await requestService.getShiftWishes();
      return res.items.map(requestFromResponse);
    },
  });
}

const APPROVED_WISHES_KEY = ['approvedWishes'];

export function useApprovedWishes(scheduleId: number | null) {
  return useQuery({
    queryKey: [...APPROVED_WISHES_KEY, scheduleId],
    queryFn: async () => {
      if (!scheduleId) return [];
      const res = await requestService.getWishesByStatus(scheduleId, 'approved');
      return res.items.map(requestFromResponse) as Request[];
    },
    enabled: !!scheduleId,
  });
}

export function useCreateShiftWish() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: Request) => {
      const dto = requestToCreate(request);
      return requestService.createShiftWish(dto);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success('Wunsch erstellt');
    },
    onError: () => {
      toast.error('Fehler beim Erstellen des Wunsches');
    },
  });
}

export function useUpdateShiftWish() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, request }: { id: string; request: Request }) => {
      const dto = requestToCreate(request);
      return requestService.updateShiftWish(Number(id), dto);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success('Wunsch aktualisiert');
    },
    onError: () => {
      toast.error('Fehler beim Aktualisieren des Wunsches');
    },
  });
}

export function useDeleteShiftWish() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => requestService.deleteShiftWish(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success('Wunsch gelöscht');
    },
    onError: () => {
      toast.error('Fehler beim Löschen des Wunsches');
    },
  });
}

export function useApproveShiftWish() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => requestService.approveShiftWish(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: APPROVED_WISHES_KEY });
      toast.success('Wunsch genehmigt');
    },
    onError: () => {
      toast.error('Fehler beim Genehmigen des Wunsches');
    },
  });
}

export function useRejectShiftWish() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason?: string }) =>
      requestService.rejectShiftWish(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: APPROVED_WISHES_KEY });
      toast.success('Wunsch abgelehnt');
    },
    onError: () => {
      toast.error('Fehler beim Ablehnen des Wunsches');
    },
  });
}
