import { useEffect, useState } from 'react';
import { Bell, BellOff, Loader2 } from 'lucide-react';
import { Button } from './ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';
import {
  onPushStateChange,
  subscribeToPush,
  unsubscribeFromPush,
  type PushState,
} from '../services/pushService';

export function PushBell() {
  const [state, setState] = useState<PushState | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    return onPushStateChange(setState);
  }, []);

  if (!state || state.permission === 'unsupported') return null;

  const isSubscribed = state.permission === 'granted' && state.subscribed;

  const handleToggle = async () => {
    setLoading(true);
    try {
      if (isSubscribed) {
        await unsubscribeFromPush();
      } else {
        await subscribeToPush();
      }
    } finally {
      setLoading(false);
    }
  };

  const tooltipText = isSubscribed
    ? 'Push-Benachrichtigungen deaktivieren'
    : 'Push-Benachrichtigungen aktivieren';

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleToggle}
            disabled={loading}
            aria-label={tooltipText}
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : isSubscribed ? (
              <Bell className="h-5 w-5 text-blue-600" />
            ) : (
              <BellOff className="h-5 w-5 text-gray-400" />
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>{tooltipText}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
