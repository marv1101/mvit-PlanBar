import { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { useTeams } from '../context/TeamContext';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Sparkles, CalendarDays, Building2 } from 'lucide-react';
import { Schedule as ScheduleType } from '../types';
import { WishReviewDialog } from '../components/WishReviewDialog';
import { ScheduleCreateForm } from '../components/schedule/ScheduleCreateForm';
import { ScheduleManageList } from '../components/schedule/ScheduleManageList';
import { toast } from 'sonner';
import * as scheduleService from '../services/scheduleService';
import { scheduleFromResponse } from '../lib/mappers';

export function Schedule() {
  const {
    employees,
    schedules,
    addSchedule,
    updateSchedule,
    deleteSchedule,
    currentWeek,
    setCurrentWeek,
    roles,
    loading,
    refresh,
  } = useApp();

  const { user } = useAuth();
  const { teams, selectedTeamId } = useTeams();
  const activeTeam = teams.find(t => t.id === selectedTeamId);

  const [activeTab, setActiveTab] = useState<'create' | 'manage'>('create');
  const [wishReviewScheduleId, setWishReviewScheduleId] = useState<number | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [currentScheduleId, setCurrentScheduleId] = useState<string | null>(null);
  const [currentScheduleStatus, setCurrentScheduleStatus] = useState<string | null>(null);
  const [pollResult, setPollResult] = useState<ScheduleType | null>(null);

  // Polling effect for TiTO submission status
  useEffect(() => {
    if (!currentScheduleId || currentScheduleStatus !== 'submitted') return;

    let mounted = true;
    const interval = setInterval(async () => {
      try {
        const res = await scheduleService.getSchedule(Number(currentScheduleId));
        if (!mounted) return;
        setCurrentScheduleStatus(res.status);
        if (res.status === 'completed') {
          clearInterval(interval);
          setSubmitting(false);
          setPollResult(scheduleFromResponse(res));
          toast.success('Schichtplan wurde von TiTO berechnet');
          refresh();
        } else if (res.status === 'failed') {
          clearInterval(interval);
          setSubmitting(false);
          setPollResult(scheduleFromResponse(res));
          const diagnostics = res.diagnostics_json as { info?: string; infeasibilityReasons?: string[] } | null;
          const reasons = diagnostics?.infeasibilityReasons;
          let msg = 'Berechnung fehlgeschlagen.';
          if (reasons && reasons.length > 0) {
            msg = reasons.slice(0, 2).join(' ');
          } else if (diagnostics?.info) {
            msg = diagnostics.info;
          }
          toast.error(msg, { duration: 8000 });
          refresh();
        }
      } catch {
        clearInterval(interval);
        if (!mounted) return;
        setSubmitting(false);
        toast.error('Fehler beim Abrufen des Status');
      }
    }, 3000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [currentScheduleId, currentScheduleStatus, refresh]);

  const handleWishReviewComplete = () => {
    const scheduleId = wishReviewScheduleId;
    setWishReviewScheduleId(null);
    if (scheduleId) {
      setSubmitting(true);
      refresh();
      scheduleService.submitScheduleToTito(scheduleId)
        .then(res => {
          setCurrentScheduleId(String(scheduleId));
          setCurrentScheduleStatus(res.status);
          toast.success('Schichtplan an TiTO übermittelt');
        })
        .catch(() => {
          setSubmitting(false);
          setCurrentScheduleId(null);
          setCurrentScheduleStatus(null);
          toast.error('Fehler beim Übermitteln an TiTO');
        });
    }
  };

  const handleWishReviewCancel = () => {
    setWishReviewScheduleId(null);
    setSubmitting(false);
    toast.info('Übermittlung abgebrochen – bitte alle ausstehenden Wünsche prüfen');
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-semibold text-2xl mb-2">Schichtplanung</h2>
        <p className="text-gray-600">Erstellen und verwalten Sie Ihre Schichtpläne</p>
        {activeTeam && (
          <div className="flex items-center gap-2 mt-2">
            <Building2 className="h-4 w-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Team: {activeTeam.name}</span>
          </div>
        )}
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'create' | 'manage')}>
        <TabsList>
          <TabsTrigger value="create">
            <Sparkles className="h-4 w-4 mr-2" />
            Neu erstellen
          </TabsTrigger>
          <TabsTrigger value="manage">
            <CalendarDays className="h-4 w-4 mr-2" />
            Verwalten ({schedules.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="create" className="space-y-6">
          <ScheduleCreateForm
            roles={roles}
            employees={employees}
            loading={loading}
            addSchedule={addSchedule}
            refresh={refresh}
            currentWeek={currentWeek}
            setCurrentWeek={setCurrentWeek}
            submitting={submitting}
            pollResult={pollResult}
            currentScheduleId={currentScheduleId}
            currentScheduleStatus={currentScheduleStatus}
            setSubmitting={setSubmitting}
            setCurrentScheduleId={setCurrentScheduleId}
            setCurrentScheduleStatus={setCurrentScheduleStatus}
            setPollResult={setPollResult}
            onWishReview={(id) => setWishReviewScheduleId(id)}
          />
        </TabsContent>

        <TabsContent value="manage" className="space-y-6">
          <ScheduleManageList
            schedules={schedules}
            loading={loading}
            employees={employees}
            roles={roles}
            currentWeek={currentWeek}
            setCurrentWeek={setCurrentWeek}
            refresh={refresh}
            submitting={submitting}
            deleteSchedule={deleteSchedule}
            updateSchedule={updateSchedule}
            onWishReview={(id) => setWishReviewScheduleId(id)}
            setCurrentScheduleId={setCurrentScheduleId}
            setCurrentScheduleStatus={setCurrentScheduleStatus}
            onCreateTab={() => setActiveTab('create')}
          />
        </TabsContent>
      </Tabs>

      {wishReviewScheduleId && (
        <WishReviewDialog
          scheduleId={wishReviewScheduleId}
          open={true}
          onOpenChange={() => setWishReviewScheduleId(null)}
          onComplete={handleWishReviewComplete}
          onCancel={handleWishReviewCancel}
          employees={employees}
        />
      )}
    </div>
  );
}
