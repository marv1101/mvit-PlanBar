import axios from 'axios';

export const KIOSK_REFETCH_INTERVAL_MS = 60 * 60 * 1000;

export interface KioskTeamDTO {
  id: number;
  name: string | null;
}

export interface KioskEmployeeDTO {
  id: number;
  name: string;
  color: string | null;
}

export interface KioskShiftDTO {
  employee_id: number;
  date: string;
  start_time: string;
  end_time: string;
  break_start: string | null;
  break_end: string | null;
  label: string | null;
  schedule_name: string | null;
}

export interface KioskBoardDTO {
  window_start: string;
  window_end: string;
  team: KioskTeamDTO | null;
  employees: KioskEmployeeDTO[];
  shifts: KioskShiftDTO[];
}

// Dedicated axios instance for the kiosk view. It deliberately does NOT use
// the shared `../lib/api` client: that client redirects to /login on 401 and
// enqueues offline mutations — both are unacceptable for the read-only kiosk.
const kioskApi = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  timeout: 15000,
});

export async function getKioskBoard(teamId?: number | null): Promise<KioskBoardDTO> {
  const { data } = await kioskApi.get<KioskBoardDTO>('/kiosk/board', {
    params: { team_id: teamId ?? undefined },
  });
  return data;
}

// POST /users/login is exempt from CSRF validation by the backend
// (see middleware/csrf.py), so no X-CSRF-Token header is needed here.
export async function kioskLogin(email: string, password: string): Promise<void> {
  await kioskApi.post('/users/login', { email, password });
}
