import React, { useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Users, ClipboardList, Calendar, Clock, TrendingUp, Briefcase, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { useNavigate } from 'react-router';
import { Shift } from '../types';
import { TIMEZONE } from '../lib/timezone';

export function Dashboard() {
  const { employees, requests, schedules, roles, loading } = useApp();
  const navigate = useNavigate();

  // Get the most recent schedule
  const latestSchedule = useMemo(() => {
    return schedules.length > 0 
      ? schedules.reduce((latest, schedule) => 
          new Date(schedule.endDate) > new Date(latest.endDate) ? schedule : latest
        )
      : null;
  }, [schedules]);

  // Calculate statistics
  const stats = useMemo(() => {
    const now = new Date();
    const todayStr = now.toISOString().split('T')[0];
    
    let totalShifts = 0;
    let todayShifts = 0;
    let upcomingShifts = 0;
    const employeeShiftCounts: Record<string, number> = {};
    const roleShiftCounts: Record<string, number> = {};

    schedules.forEach(schedule => {
      totalShifts += schedule.shifts.length;
      
      schedule.shifts.forEach(shift => {
        // Count per employee
        employeeShiftCounts[shift.employeeId] = (employeeShiftCounts[shift.employeeId] || 0) + 1;
        
        // Count per role
        const employee = employees.find(e => e.id === shift.employeeId);
        if (employee) {
          employee.roles.forEach(roleId => {
            roleShiftCounts[roleId] = (roleShiftCounts[roleId] || 0) + 1;
          });
        }

        // Today's shifts
        if (shift.date === todayStr) {
          todayShifts++;
        }

        // Upcoming shifts (next 7 days)
        const shiftDate = new Date(shift.date);
        const daysUntilShift = Math.ceil((shiftDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
        if (daysUntilShift >= 0 && daysUntilShift <= 7) {
          upcomingShifts++;
        }
      });
    });

    // Calculate average shifts per employee
    const avgShiftsPerEmployee = employees.length > 0 
      ? (totalShifts / employees.length).toFixed(1) 
      : '0';

    // Request types breakdown
    const requestsByType = requests.reduce((acc, req) => {
      acc[req.type] = (acc[req.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      totalShifts,
      todayShifts,
      upcomingShifts,
      avgShiftsPerEmployee,
      employeeShiftCounts,
      roleShiftCounts,
      requestsByType,
    };
  }, [schedules, employees, requests, roles]);

  const mainStats = [
    {
      title: 'Mitarbeiter',
      value: employees.length,
      icon: Users,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      description: 'Registrierte Mitarbeiter',
    },
    {
      title: "Heutige Schichten",
      value: stats.todayShifts,
      icon: Clock,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
      description: 'Aktive Schichten heute',
    },
    {
      title: 'Offene Wünsche',
      value: requests.length,
      icon: ClipboardList,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      description: 'Zu berücksichtigende Anfragen',
    },
    {
      title: 'Schichtpläne',
      value: schedules.length,
      icon: Calendar,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      description: 'Gespeicherte Pläne',
    },
  ];

  // Top 5 employees by shift count
  const topEmployees = useMemo(() => {
    return Object.entries(stats.employeeShiftCounts)
      .map(([employeeId, count]) => ({
        employee: employees.find(e => e.id === employeeId),
        count,
      }))
      .filter(item => item.employee)
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
  }, [stats.employeeShiftCounts, employees]);

  // Role distribution
  const roleDistribution = useMemo(() => {
    return Object.entries(stats.roleShiftCounts)
      .map(([roleId, count]) => ({
        role: roles.find(r => r.id === roleId),
        count,
      }))
      .filter(item => item.role)
      .sort((a, b) => b.count - a.count);
  }, [stats.roleShiftCounts, roles]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="font-semibold text-2xl mb-2">Dashboard</h2>
          <p className="text-gray-600">Überblick über Ihre Schichtplanung</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-8 w-8 mx-auto text-blue-600 mb-4 animate-spin" />
            <p className="text-gray-600">Lade Daten...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-semibold text-2xl mb-2">Dashboard</h2>
        <p className="text-gray-600">Überblick über Ihre Schichtplanung</p>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {mainStats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.title}>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-2">
                  <div className={`${stat.bgColor} p-3 rounded-full`}>
                    <Icon className={`h-6 w-6 ${stat.color}`} />
                  </div>
                  <p className="text-3xl font-semibold">{stat.value}</p>
                </div>
                <p className="text-sm font-medium text-gray-900">{stat.title}</p>
                <p className="text-xs text-gray-500 mt-1">{stat.description}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Additional Statistics */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Statistiken
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-gray-600">Gesamt Schichten</span>
              <span className="font-semibold text-lg">{stats.totalShifts}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-gray-600">Nächste 7 Tage</span>
              <span className="font-semibold text-lg">{stats.upcomingShifts}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-gray-600">⌀ Schichten/Mitarbeiter</span>
              <span className="font-semibold text-lg">{stats.avgShiftsPerEmployee}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-gray-600">Definierte Rollen</span>
              <span className="font-semibold text-lg">{roles.length}</span>
            </div>
          </CardContent>
        </Card>

        {/* Request Types Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClipboardList className="h-5 w-5" />
              Wünsche nach Typ
            </CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(stats.requestsByType).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(stats.requestsByType).map(([type, count]) => {
                  const typeLabels: Record<string, { label: string; color: string }> = {
                    'bevorzugt': { label: 'Bevorzugt', color: 'bg-green-500' },
                    'urlaubswunsch': { label: 'Urlaub', color: 'bg-blue-500' },
                    'nicht-verfügbar': { label: 'Nicht verfügbar', color: 'bg-red-500' },
                  };
                  const info = typeLabels[type] || { label: type, color: 'bg-gray-500' };
                  
                  return (
                    <div key={type} className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${info.color}`} />
                      <span className="flex-1 text-gray-700">{info.label}</span>
                      <span className="font-semibold">{count}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">Keine Wünsche vorhanden</p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Employees by Shifts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Meiste Schichten
            </CardTitle>
            <CardDescription>Top 5 Mitarbeiter nach Schichtanzahl</CardDescription>
          </CardHeader>
          <CardContent>
            {topEmployees.length > 0 ? (
              <div className="space-y-3">
                {topEmployees.map(({ employee, count }, index) => (
                  <div key={employee!.id} className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full flex items-center justify-center bg-gray-100 font-semibold text-sm">
                      {index + 1}
                    </div>
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: employee!.color }}
                    />
                    <span className="flex-1 font-medium">{employee!.name}</span>
                    <span className="text-gray-600">{count} Schichten</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">Noch keine Schichten verteilt</p>
            )}
          </CardContent>
        </Card>

        {/* Role Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Briefcase className="h-5 w-5" />
              Rollen-Verteilung
            </CardTitle>
            <CardDescription>Schichten nach Rollen</CardDescription>
          </CardHeader>
          <CardContent>
            {roleDistribution.length > 0 ? (
              <div className="space-y-3">
                {roleDistribution.map(({ role, count }) => {
                  const percentage = stats.totalShifts > 0 
                    ? ((count / stats.totalShifts) * 100).toFixed(1) 
                    : '0';
                  
                  return (
                    <div key={role!.id} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: role!.color }}
                          />
                          <span className="font-medium">{role!.name}</span>
                        </div>
                        <span className="text-sm text-gray-600">
                          {count} ({percentage}%)
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="h-2 rounded-full"
                          style={{ 
                            backgroundColor: role!.color, 
                            width: `${percentage}%` 
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">Noch keine Rollen-Daten verfügbar</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Schnellstart</CardTitle>
          <CardDescription>Erstellen und verwalten Sie Ihre Schichtpläne</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            <Button onClick={() => navigate('/employees')} variant="outline" className="w-full">
              <Users className="h-4 w-4 mr-2" />
              Mitarbeiter
            </Button>
            <Button onClick={() => navigate('/requests')} variant="outline" className="w-full">
              <ClipboardList className="h-4 w-4 mr-2" />
              Wünsche
            </Button>
            <Button onClick={() => navigate('/schedule')} variant="outline" className="w-full">
              <Calendar className="h-4 w-4 mr-2" />
              Schichtplan
            </Button>
            <Button onClick={() => navigate('/employee-view')} variant="outline" className="w-full">
              <Users className="h-4 w-4 mr-2" />
              Mitarbeiteransicht
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Latest Schedule Info */}
      {latestSchedule && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Aktuellster Schichtplan
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-600">Name:</span>
                <span className="font-medium">{latestSchedule.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Zeitraum:</span>
                <span className="font-medium">
                  {new Date(latestSchedule.startDate).toLocaleDateString('de-DE', { timeZone: TIMEZONE })} - {' '}
                  {new Date(latestSchedule.endDate).toLocaleDateString('de-DE', { timeZone: TIMEZONE })}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Schichten:</span>
                <span className="font-medium">{latestSchedule.shifts.length}</span>
              </div>
              <Button 
                onClick={() => navigate('/schedule')} 
                className="w-full mt-4"
              >
                Zum Schichtplan
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
