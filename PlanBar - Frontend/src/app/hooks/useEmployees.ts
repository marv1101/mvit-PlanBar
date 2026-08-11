import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as employeeService from '../services/employeeService';
import { employeeFromResponse, employeeToCreate } from '../lib/mappers';
import { Employee } from '../types';
import { toast } from 'sonner';

const QUERY_KEY = ['employees'];

export function useEmployees() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const res = await employeeService.getEmployees();
      return res.items.map(employeeFromResponse);
    },
  });
}

export function useCreateEmployee() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (employee: Employee) => {
      const dto = employeeToCreate(employee);
      return employeeService.createEmployee(dto);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success('Mitarbeiter erstellt');
    },
    onError: () => {
      toast.error('Fehler beim Erstellen des Mitarbeiters');
    },
  });
}

export function useUpdateEmployee() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, employee }: { id: string; employee: Employee }) => {
      const dto = employeeToCreate(employee);
      return employeeService.updateEmployee(Number(id), dto);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success('Mitarbeiter aktualisiert');
    },
    onError: (error: unknown) => {
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        toast.error('Die Daten wurden inzwischen geändert. Bitte Seite neu laden.');
        queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      } else {
        toast.error('Fehler beim Aktualisieren des Mitarbeiters');
      }
    },
  });
}

export function useDeleteEmployee() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => employeeService.deleteEmployee(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ['shiftWishes'] });
      toast.success('Mitarbeiter gelöscht');
    },
    onError: () => {
      toast.error('Fehler beim Löschen des Mitarbeiters');
    },
  });
}
