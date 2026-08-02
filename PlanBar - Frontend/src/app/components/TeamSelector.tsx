import { Building2, ChevronDown } from 'lucide-react';
import { useTeams } from '../context/TeamContext';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

export function TeamSelector() {
  const { teams, selectedTeamId, setSelectedTeamId, loading } = useTeams();

  if (loading || teams.length <= 1) {
    return null;
  }

  return (
    <div className="flex items-center gap-2">
      <Building2 className="h-4 w-4 text-gray-500" />
      <Select value={selectedTeamId ?? ''} onValueChange={(value) => setSelectedTeamId(value || null)}>
        <SelectTrigger className="w-[200px]">
          <SelectValue placeholder="Team auswählen" />
        </SelectTrigger>
        <SelectContent>
          {teams.map((team) => (
            <SelectItem key={team.id} value={team.id}>
              <div className="flex items-center gap-2">
                {team.color && (
                  <span
                    className="inline-block w-3 h-3 rounded-full"
                    style={{ backgroundColor: team.color }}
                  />
                )}
                {team.name}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
