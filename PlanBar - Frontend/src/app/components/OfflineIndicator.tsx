import { WifiOff, CloudOff, RefreshCw } from 'lucide-react';
import { useOnlineStatus } from '../hooks/useOnlineStatus';
import { syncManager } from '../lib/syncManager';
import { useState } from 'react';
import { Button } from './ui/button';

export function OfflineIndicator() {
  const { isOnline, wasOffline } = useOnlineStatus();
  const [isSyncing, setIsSyncing] = useState(false);

  if (isOnline && !wasOffline) return null;

  async function handleSync() {
    setIsSyncing(true);
    try {
      await syncManager.processQueue();
    } finally {
      setIsSyncing(false);
    }
  }

  if (!isOnline) {
    return (
      <div className="fixed bottom-4 right-4 z-50 flex items-center gap-2 rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 shadow-lg">
        <WifiOff className="h-4 w-4 text-amber-600" />
        <span className="text-sm font-medium text-amber-800">Offline</span>
        <span className="text-xs text-amber-600">Änderungen werden lokal gespeichert</span>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex items-center gap-2 rounded-lg bg-green-50 border border-green-200 px-4 py-3 shadow-lg">
      <CloudOff className="h-4 w-4 text-green-600" />
      <span className="text-sm font-medium text-green-800">Wieder online</span>
      <Button
        variant="outline"
        size="sm"
        onClick={handleSync}
        disabled={isSyncing}
        className="ml-2 h-7 text-xs"
      >
        <RefreshCw className={`mr-1 h-3 w-3 ${isSyncing ? 'animate-spin' : ''}`} />
        {isSyncing ? 'Synchronisiere...' : 'Synchronisieren'}
      </Button>
    </div>
  );
}
