import { Badge } from '../ui/badge';

const STATUS_LABELS: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  draft: { label: 'Entwurf', variant: 'secondary' },
  review: { label: 'In Prüfung', variant: 'default' },
  submitted: { label: 'Wird berechnet...', variant: 'default' },
  completed: { label: 'Abgeschlossen', variant: 'outline' },
  failed: { label: 'Fehlgeschlagen', variant: 'destructive' },
};

export function StatusBadge({ status }: { status: string }) {
  const config = STATUS_LABELS[status] || { label: status, variant: 'secondary' as const };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
