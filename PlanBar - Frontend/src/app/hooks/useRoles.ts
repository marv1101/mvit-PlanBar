import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as roleService from '../services/roleService';
import { roleFromResponse, roleToCreate } from '../lib/mappers';
import { Role } from '../types';
import { toast } from 'sonner';

const QUERY_KEY = ['roles'];

export function useRoles() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const res = await roleService.getRoles();
      return res.items.map(roleFromResponse);
    },
  });
}

export function useCreateRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (role: Role) => {
      const dto = roleToCreate(role);
      return roleService.createRole(dto);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success('Rolle erstellt');
    },
    onError: () => {
      toast.error('Fehler beim Erstellen der Rolle');
    },
  });
}

export function useUpdateRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, role }: { id: string; role: Role }) => {
      const dto = roleToCreate(role);
      return roleService.updateRole(Number(id), dto);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success('Rolle aktualisiert');
    },
    onError: () => {
      toast.error('Fehler beim Aktualisieren der Rolle');
    },
  });
}

export function useDeleteRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => roleService.deleteRole(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success('Rolle gelöscht');
    },
    onError: () => {
      toast.error('Fehler beim Löschen der Rolle');
    },
  });
}
