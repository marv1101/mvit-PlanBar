import React, { useEffect, useRef, useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Textarea } from './ui/textarea';
import { Badge } from './ui/badge';
import { CheckCircle, XCircle, Loader2, AlertTriangle } from 'lucide-react';
import * as requestService from '../services/requestService';
import { requestFromResponse } from '../lib/mappers';
import { Request, Employee } from '../types';
import { toast } from 'sonner';

interface WishReviewDialogProps {
  scheduleId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onComplete: () => void;
  onCancel: () => void;
  employees: Employee[];
}

export function WishReviewDialog({ scheduleId, open, onOpenChange, onComplete, onCancel, employees }: WishReviewDialogProps) {
  const [wishes, setWishes] = useState<Request[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [rejectReasons, setRejectReasons] = useState<Record<string, string>>({});
  const isProcessingRef = useRef(false);

  useEffect(() => {
    if (!open) return;

    let mounted = true;
    setLoading(true);
    requestService.getPendingShiftWishes(scheduleId)
      .then(res => {
        if (!mounted) return;
        setWishes(res.items.map(requestFromResponse));
      })
      .catch(() => {
        if (!mounted) return;
        toast.error('Fehler beim Laden der ausstehenden Wünsche');
        setWishes([]);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => { mounted = false; };
  }, [scheduleId, open]);

  const getEmployeeName = (employeeId: string) => {
    const emp = employees.find(e => e.id === employeeId);
    return emp?.name || 'Unbekannt';
  };

  const handleApprove = async (wishId: string) => {
    if (isProcessingRef.current) return;
    isProcessingRef.current = true;
    setProcessingId(wishId);
    try {
      await requestService.approveShiftWish(Number(wishId));
      setWishes(prev => prev.filter(w => w.id !== wishId));
      toast.success('Wunsch freigegeben');
    } catch {
      toast.error('Fehler beim Freigeben des Wunsches');
    } finally {
      isProcessingRef.current = false;
      setProcessingId(null);
    }
  };

  const handleReject = async (wishId: string) => {
    if (isProcessingRef.current) return;
    isProcessingRef.current = true;
    setProcessingId(wishId);
    try {
      await requestService.rejectShiftWish(Number(wishId), rejectReasons[wishId]);
      setWishes(prev => prev.filter(w => w.id !== wishId));
      setRejectReasons(prev => { const r = { ...prev }; delete r[wishId]; return r; });
      toast.success('Wunsch abgelehnt');
    } catch {
      toast.error('Fehler beim Ablehnen des Wunsches');
    } finally {
      isProcessingRef.current = false;
      setProcessingId(null);
    }
  };

  const allReviewed = wishes.length === 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            Ausstehende Wünsche prüfen
          </DialogTitle>
          <DialogDescription>
            {loading
              ? 'Lade ausstehende Wünsche...'
              : allReviewed
                ? 'Alle Wünsche wurden geprüft. Die Übermittlung kann fortgesetzt werden.'
                : `${wishes.length} Wunsch/Wünsche müssen vor der Übermittlung freigegeben oder abgelehnt werden.`
            }
          </DialogDescription>
        </DialogHeader>

        {loading && (
          <div className="py-12 text-center">
            <Loader2 className="h-8 w-8 mx-auto text-blue-600 mb-4 animate-spin" />
            <p className="text-sm text-gray-500">Lade Wünsche...</p>
          </div>
        )}

        {!loading && wishes.length > 0 && (
          <div className="space-y-3">
            {wishes.map(wish => (
              <Card key={wish.id}>
                <CardContent className="pt-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm">{getEmployeeName(wish.employeeId)}</p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {new Date(wish.date).toLocaleDateString('de-DE', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {wish.type === 'urlaubswunsch' ? 'Urlaub' : wish.type === 'bevorzugt' ? 'Bevorzugt' : 'Nicht verfügbar'}
                        </Badge>
                        <span className="text-xs text-gray-400">Woche {wish.week}</span>
                      </div>
                      {wish.notes && (
                        <p className="text-xs text-gray-500 mt-1 italic">{wish.notes}</p>
                      )}
                    </div>

                    <div className="flex flex-col gap-2 shrink-0">
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-green-600 border-green-300 hover:bg-green-50"
                        onClick={() => handleApprove(wish.id)}
                        disabled={processingId === wish.id}
                      >
                        {processingId === wish.id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <CheckCircle className="h-3 w-3 mr-1" />
                        )}
                        Freigeben
                      </Button>

                      <div className="flex gap-2 items-start">
                        <Textarea
                          className="min-h-[32px] text-xs py-1 px-2 w-32"
                          placeholder="Grund (optional)"
                          value={rejectReasons[wish.id] || ''}
                          onChange={e => setRejectReasons(prev => ({ ...prev, [wish.id]: e.target.value }))}
                          maxLength={500}
                        />
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-red-600 border-red-300 hover:bg-red-50 shrink-0"
                          onClick={() => handleReject(wish.id)}
                          disabled={processingId === wish.id}
                        >
                          {processingId === wish.id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <XCircle className="h-3 w-3 mr-1" />
                          )}
                          Ablehnen
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {!loading && wishes.length === 0 && (
          <div className="py-8 text-center text-green-600">
            <CheckCircle className="h-8 w-8 mx-auto mb-2" />
            <p className="font-medium">Alle Wünsche geprüft</p>
            <p className="text-sm mt-1">Es sind keine ausstehenden Wünsche mehr vorhanden.</p>
          </div>
        )}

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onCancel}>
            Abbrechen
          </Button>
          <Button onClick={onComplete} disabled={!allReviewed}>
            {allReviewed ? 'Weiter zur Übermittlung' : `${wishes.length} Wunsch/Wünsche prüfen`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}