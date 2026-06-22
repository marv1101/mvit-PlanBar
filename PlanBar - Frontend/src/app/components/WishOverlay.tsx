import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Request, Employee } from '../../types';
import { START_HOUR, HOUR_HEIGHT, toMinutes, formatTime } from './schedule/shared/CalendarUtils';
import { Ban, Calendar, Star, Clock } from 'lucide-react';

// Colors for different wish types
const WISH_COLORS: Record<string, { bg: string; border: string; text: string; icon: React.ReactNode }> = {
  'urlaubswunsch': {
    bg: 'rgba(59, 130, 246, 0.15)', // blue
    border: 'rgba(59, 130, 246, 0.4)',
    text: 'text-blue-700',
    icon: <Calendar className="h-3 w-3" />,
  },
  'bevorzugt': {
    bg: 'rgba(34, 197, 94, 0.15)', // green
    border: 'rgba(34, 197, 94, 0.4)',
    text: 'text-green-700',
    icon: <Star className="h-3 w-3" />,
  },
  'nicht-verfügbar': {
    bg: 'rgba(239, 68, 68, 0.15)', // red
    border: 'rgba(239, 68, 68, 0.4)',
    text: 'text-red-700',
    icon: <Ban className="h-3 w-3" />,
  },
};

interface WishOverlayProps {
  wish: Request;
  employee?: Employee;
  onClick?: (wish: Request) => void;
}

export function WishOverlay({ wish, employee, onClick }: WishOverlayProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  const colors = WISH_COLORS[wish.type] || WISH_COLORS['bevorzugt'];
  const employeeName = employee?.name || 'Unbekannt';

  // Calculate position based on wish time
  // For all-day wishes (like vacation), we'll show a subtle indicator
  // For time-specific wishes, we'll show an overlay similar to breaks
  const isAllDay = wish.type === 'urlaubswunsch' || wish.type === 'nicht-verfügbar';

  if (isAllDay) {
    // All-day wish: show a subtle banner at the top of the day column
    return (
      <div
        className="relative cursor-pointer"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onClick={() => onClick?.(wish)}
      >
        <div
          className="w-full py-1 px-2 border-l-2 rounded-r"
          style={{
            backgroundColor: colors.bg,
            borderLeftColor: colors.border,
          }}
        >
          <div className={`flex items-center gap-1 text-[10px] font-medium ${colors.text} truncate`}>
            {colors.icon}
            <span>{employeeName}</span>
            <span className="text-gray-500">•</span>
            <span className="capitalize">{wish.type}</span>
          </div>
        </div>

        {/* Tooltip */}
        <AnimatePresence>
          {showTooltip && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              className="absolute z-50 left-0 right-0 top-full mt-1"
            >
              <div className="bg-white rounded-lg shadow-lg border p-2 text-xs">
                <div className="font-medium">{employeeName}</div>
                <div className={`capitalize ${colors.text}`}>{wish.type}</div>
                {wish.notes && (
                  <div className="text-gray-500 mt-1 italic">{wish.notes}</div>
                )}
                {wish.type === 'nicht-verfügbar' && (
                  <div className="text-red-600 mt-1 font-medium">
                    ⚠️ Keine Schicht zuweisen
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }

  // Time-specific wish: show overlay within the day column
  // For now, we'll show a subtle indicator since the Request type doesn't have specific times
  return null;
}

// Helper function to get wish style for positioning (similar to getBreakStyle)
export function getWishOverlayStyle(wish: Request) {
  // For time-specific wishes, calculate position
  // Since our current Request type doesn't have start/end times,
  // we'll return a full-height overlay for all-day wishes
  const isAllDay = wish.type === 'urlaubswunsch' || wish.type === 'nicht-verfügbar';
  
  if (isAllDay) {
    return {
      top: '0px',
      height: '100%',
      opacity: 0.15,
    };
  }

  return null;
}
