import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../ui/alert-dialog';
import type { ArbZgWarning } from '../../types';

interface ArbZgConfirmDialogProps {
  open: boolean;
  warnings: ArbZgWarning[];
  onConfirm: () => void;
  onCancel: () => void;
}

export function ArbZgConfirmDialog({ open, warnings, onConfirm, onCancel }: ArbZgConfirmDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={(open) => { if (!open) onCancel(); }}>
      <AlertDialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2 text-amber-700">
            <span className="text-xl">⚠️</span>
            ArbZG-Verstöße erkannt
          </AlertDialogTitle>
          <AlertDialogDescription>
            Die folgenden Regelverstöße wurden im Schichtplan festgestellt:
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="space-y-2 my-4">
          {warnings.map((warning, i) => (
            <div
              key={i}
              className="border border-amber-200 bg-amber-50 rounded-lg p-3 text-sm"
            >
              <div className="font-medium text-amber-800 capitalize">
                {warning.rule.replace('_', ' ')}
              </div>
              <div className="text-amber-700 mt-1">{warning.message}</div>
              {warning.shift_date && (
                <div className="text-amber-600 text-xs mt-1">
                  Datum: {warning.shift_date}
                </div>
              )}
            </div>
          ))}
        </div>

        <AlertDialogFooter className="flex-col sm:flex-row gap-2">
          <AlertDialogCancel onClick={onCancel} className="w-full sm:w-auto">
            Bearbeiten fortsetzen
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            className="w-full sm:w-auto bg-amber-600 hover:bg-amber-700"
          >
            Trotzdem speichern
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
