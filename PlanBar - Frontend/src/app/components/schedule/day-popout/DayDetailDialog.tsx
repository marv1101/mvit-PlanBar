import React, { useEffect } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../../ui/dialog';
import { Button } from '../../ui/button';

interface DayDetailDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  showNavigation?: boolean;
  fullScreen?: boolean;
  hasPrev: boolean;
  hasNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  children: React.ReactNode;
}

export function DayDetailDialog({
  open,
  onOpenChange,
  title,
  description,
  showNavigation = false,
  fullScreen = false,
  hasPrev,
  hasNext,
  onPrev,
  onNext,
  children,
}: DayDetailDialogProps) {
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (showNavigation && e.key === 'ArrowLeft' && hasPrev) onPrev();
      if (showNavigation && e.key === 'ArrowRight' && hasNext) onNext();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, showNavigation, hasPrev, hasNext, onPrev, onNext]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        overlayClassName="bg-black/60 backdrop-blur-sm"
        className={
          fullScreen
            ? 'w-screen max-w-none sm:max-w-none h-screen overflow-hidden grid-rows-[auto_1fr] rounded-none border-0 p-4'
            : 'w-[95vw] max-w-none sm:max-w-none h-[92vh] overflow-auto grid-rows-[auto_1fr]'
        }
        onKeyDown={(e) => {
          if (!showNavigation) return;
          if (e.key === 'ArrowLeft' && hasPrev) onPrev();
          if (e.key === 'ArrowRight' && hasNext) onNext();
        }}
      >
        <DialogHeader>
          <div className="flex items-center gap-2">
            {showNavigation && (
              <Button
                size="icon"
                variant="ghost"
                aria-label="Voriger Tag"
                disabled={!hasPrev}
                onClick={onPrev}
              >
                <ChevronLeft className="h-5 w-5" />
              </Button>
            )}
            <DialogTitle className="text-xl">{title}</DialogTitle>
            {showNavigation && (
              <Button
                size="icon"
                variant="ghost"
                aria-label="Nächster Tag"
                disabled={!hasNext}
                onClick={onNext}
              >
                <ChevronRight className="h-5 w-5" />
              </Button>
            )}
          </div>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <div className="h-full min-h-0">{children}</div>
      </DialogContent>
    </Dialog>
  );
}
