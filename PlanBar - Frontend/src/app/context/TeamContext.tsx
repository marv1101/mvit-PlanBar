import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { toast } from 'sonner';
import { Team } from '../types';
import * as teamService from '../services/teamService';
import { useAuth } from './AuthContext';

interface TeamContextType {
  teams: Team[];
  selectedTeamId: string | null;
  setSelectedTeamId: (id: string | null) => void;
  loading: boolean;
  refresh: () => Promise<void>;
}

export const TeamContext = createContext<TeamContextType | undefined>(undefined);

export function TeamProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = React.useCallback(async () => {
    if (!user) {
      setTeams([]);
      setSelectedTeamId(null);
      return;
    }
    // Admins manage teams via the dedicated Teams page and don't need an active team here.
    if (user.role === 'admin') {
      setTeams([]);
      setSelectedTeamId(null);
      return;
    }
    setLoading(true);
    try {
      const data = await teamService.getMyTeams();
      setTeams(data);
      if (data.length === 1) {
        setSelectedTeamId(data[0].id);
      } else if (data.length === 0) {
        setSelectedTeamId(null);
      }
      // If the currently selected team is no longer available, reset it.
      else if (selectedTeamId && !data.some((t) => t.id === selectedTeamId)) {
        setSelectedTeamId(null);
      }
    } catch {
      toast.error('Fehler beim Laden der Teams');
    } finally {
      setLoading(false);
    }
  }, [user, selectedTeamId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <TeamContext.Provider value={{ teams, selectedTeamId, setSelectedTeamId, loading, refresh }}>
      {children}
    </TeamContext.Provider>
  );
}

export function useTeams() {
  const context = useContext(TeamContext);
  if (context === undefined) {
    throw new Error('useTeams must be used within a TeamProvider');
  }
  return context;
}
