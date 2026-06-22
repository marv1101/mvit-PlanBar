import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Request, Employee } from '../../types';
import { Ban, Calendar, Star } from 'lucide-react';

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

  // All-day wishes (vacation / unavailable): show a full-width banner at the top of the day column
  if (wish.type === 'urlaubswunsch' || wish.type === 'nicht-verfügbar') {
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

  // 'bevorzugt' (preferred) wishes: show a smaller inline indicator
  if (wish.type === 'bevorzugt') {
    return (
      <div
        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium cursor-pointer"
        style={{
          backgroundColor: colors.bg,
          borderLeftColor: colors.border,
          borderLeftWidth: '2px',
        }}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onClick={() => onClick?.(wish)}
      >
        {colors.icon}
        <span className={colors.text}>{employeeName}</span>
        <AnimatePresence>
          {showTooltip && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              className="absolute z-50 left-0 right-0 top-full mt-1"
            >
              <div className="bg-white rounded-lg shadow-lg border p-2 text-xs whitespace-nowrap">
                <div className="font-medium">{employeeName}</div>
                <div className={`capitalize ${colors.text}`}>{wish.type}</div>
                {wish.notes && <div className="text-gray-500 mt-1 italic">{wish.notes}</div>}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  }

  // Other / unknown wish types: render nothing
  return null;
}
