import { useQuery } from '@tanstack/react-query';
import { getKioskBoard, KIOSK_REFETCH_INTERVAL_MS } from '../services/kioskService';

export function useKioskBoard(teamId?: number | null) {
  return useQuery({
    queryKey: ['kiosk-board', teamId ?? null],
    queryFn: () => getKioskBoard(teamId),
    refetchInterval: KIOSK_REFETCH_INTERVAL_MS,
    refetchOnWindowFocus: false,
    retry: 1,
  });
}
