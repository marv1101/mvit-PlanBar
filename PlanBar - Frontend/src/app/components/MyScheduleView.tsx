import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Calendar, Clock, Coffee, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { getMySchedule } from '../services/selfService';
import { TIMEZONE } from '../lib/timezone';

const weekDays = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

export function MyScheduleView() {
  const { data: shifts, isLoading, error } = useQuery({
    queryKey: ['my-schedule'],
    queryFn: getMySchedule,
  });

  const { shiftsByDate, calendarWeeks, totalHours } = useMemo(() => {
    if (!shifts || shifts.length === 0) return { shiftsByDate: {} as Record<string, typeof shifts>, calendarWeeks: [] as Date[][], totalHours: 0 };

    const byDate: Record<string, typeof shifts> = {};
    let hours = 0;
    for (const s of shifts) {
      if (!byDate[s.date]) byDate[s.date] = [];
      byDate[s.date].push(s);
      const [sh, sm] = s.start_time.split(':').map(Number);
      const [eh, em] = s.end_time.split(':').map(Number);
      let mins = (eh * 60 + em) - (sh * 60 + sm);
      if (s.break_start && s.break_end) {
        const [bsh, bsm] = s.break_start.split(':').map(Number);
        const [beh, bem] = s.break_end.split(':').map(Number);
        mins -= (beh * 60 + bem) - (bsh * 60 + bsm);
      }
      hours += mins / 60;
    }

    const minDate = shifts.reduce((a, b) => a.date < b.date ? a : b, shifts[0]);
    const maxDate = shifts.reduce((a, b) => a.date > b.date ? a : b, shifts[0]);
    const start = new Date(minDate.date);
    const end = new Date(maxDate.date);
    const days: Date[] = [];
    const cur = new Date(start);
    while (cur <= end) {
      days.push(new Date(cur));
      cur.setDate(cur.getDate() + 1);
    }

    const weeks: Date[][] = [];
    let curWeek: Date[] = [];
    days.forEach((day, i) => {
      if (day.getDay() === 1 && curWeek.length > 0) {
        weeks.push(curWeek);
        curWeek = [];
      }
      curWeek.push(day);
      if (i === days.length - 1) weeks.push(curWeek);
    });

    return { shiftsByDate: byDate, calendarDays: days, calendarWeeks: weeks, totalHours: hours.toFixed(1) };
  }, [shifts]);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Loader2 className="h-8 w-8 mx-auto text-blue-600 mb-4 animate-spin" />
          <p className="text-gray-600">Lade Dienstplan...</p>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-red-600">Fehler beim Laden des Dienstplans</p>
        </CardContent>
      </Card>
    );
  }

  if (!shifts || shifts.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Calendar className="h-12 w-12 mx-auto text-gray-400 mb-4" />
          <p className="text-gray-600">Keine Schichten gefunden</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-2xl font-semibold">{shifts.length}</p>
            <p className="text-sm text-gray-600 mt-1">Schichten</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-2xl font-semibold">{totalHours}h</p>
            <p className="text-sm text-gray-600 mt-1">Gesamtzeit</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Kalenderansicht
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="border rounded-lg overflow-x-auto">
            <div className="min-w-[600px]">
              <div className="grid grid-cols-7 bg-gray-100 border-b">
                {weekDays.map(day => (
                  <div key={day} className="p-2 text-center font-medium text-sm">{day}</div>
                ))}
              </div>
              {calendarWeeks.map((week, wi) => (
                <div key={wi} className="grid grid-cols-7">
                  {week.map((day) => {
                    const dateStr = day.toISOString().split('T')[0];
                    const dayShifts = shiftsByDate[dateStr] || [];
                    const isToday = day.toDateString() === new Date().toDateString();
                    return (
                      <div
                        key={day.toISOString()}
                        className={`border p-1 min-h-[90px] ${isToday ? 'bg-blue-50' : ''} ${dayShifts.length > 0 ? 'bg-green-50/50' : ''}`}
                      >
                        <div className="font-medium text-xs mb-1 text-gray-700">{day.getDate()}</div>
                        {dayShifts.map(s => (
                          <div key={s.id} className="bg-blue-100 rounded px-1 py-0.5 mb-0.5 text-xs">
                            <div className="font-medium">{s.start_time.slice(0, 5)} - {s.end_time.slice(0, 5)}</div>
                            {s.break_start && s.break_end && (
                              <div className="text-gray-500 text-[10px]">
                                {s.break_start.slice(0, 5)}-{s.break_end.slice(0, 5)}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Schichtliste
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {shifts.map(s => {
              const date = new Date(s.date);
              const weekday = date.toLocaleDateString('de-DE', { timeZone: TIMEZONE, weekday: 'long' });
              return (
                <div key={s.id} className="border rounded-lg p-3 border-l-4 border-l-blue-500">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-sm">
                        {date.toLocaleDateString('de-DE', { timeZone: TIMEZONE })} - {weekday}
                      </p>
                      <div className="flex items-center gap-3 mt-1 text-xs text-gray-600">
                        <span>{s.start_time.slice(0, 5)} - {s.end_time.slice(0, 5)}</span>
                        {s.break_start && s.break_end && (
                          <span className="flex items-center gap-1">
                            <Coffee className="h-3 w-3" />
                            {s.break_start.slice(0, 5)} - {s.break_end.slice(0, 5)}
                          </span>
                        )}
                        {s.label && <Badge variant="outline" className="text-[10px]">{s.label}</Badge>}
                      </div>
                    </div>
                    <Badge variant="secondary" className="text-xs">{s.schedule_name}</Badge>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
