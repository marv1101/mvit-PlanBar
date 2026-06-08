import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Loader2, TrendingUp, TrendingDown, Minus, Clock } from 'lucide-react';
import { EmployeeTimeAccount } from '../types';
import * as employeeService from '../services/employeeService';
import { timeAccountFromResponse } from '../lib/mappers';

function balanceColor(balance: number): string {
  if (Math.abs(balance) <= 5) return 'text-green-600 bg-green-50 border-green-200';
  if (Math.abs(balance) <= 15) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
  return 'text-red-600 bg-red-50 border-red-200';
}

function balanceBg(balance: number): string {
  if (Math.abs(balance) <= 5) return 'bg-green-100';
  if (Math.abs(balance) <= 15) return 'bg-yellow-100';
  return 'bg-red-100';
}

function BalanceIcon({ balance }: { balance: number }) {
  if (balance > 1) return <TrendingUp className="h-5 w-5" />;
  if (balance < -1) return <TrendingDown className="h-5 w-5" />;
  return <Minus className="h-5 w-5" />;
}

interface TimeAccountCardProps {
  employeeId: string;
}

export function TimeAccountCard({ employeeId }: TimeAccountCardProps) {
  const [data, setData] = useState<EmployeeTimeAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!employeeId) return;

    setLoading(true);
    setError(null);

    employeeService.getEmployeeTimeAccount(Number(employeeId))
      .then(res => {
        setData(timeAccountFromResponse(res));
      })
      .catch(() => {
        setError('Fehler beim Laden des Zeitkontos');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [employeeId]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Zeitkonto
          </CardTitle>
        </CardHeader>
        <CardContent className="py-8 text-center">
          <Loader2 className="h-6 w-6 mx-auto text-blue-600 mb-2 animate-spin" />
          <p className="text-sm text-gray-500">Lade Zeitkonto...</p>
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Zeitkonto
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">{error || 'Keine Daten verfügbar'}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5" />
          Zeitkonto
        </CardTitle>
        <CardDescription>Aktueller Saldo und Historie</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className={`rounded-lg border-2 p-4 ${balanceColor(data.currentBalance)}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Aktueller Saldo</p>
              <p className="text-3xl font-bold mt-1">
                {data.currentBalance > 0 ? '+' : ''}{data.currentBalance.toFixed(1)}h
              </p>
            </div>
            <div className={`p-3 rounded-full ${balanceBg(data.currentBalance)}`}>
              <BalanceIcon balance={data.currentBalance} />
            </div>
          </div>
        </div>

        {data.projected && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-xs font-medium text-blue-700 mb-1">Prognose nach aktuellem Plan</p>
            <div className="flex justify-between text-sm">
              <span className="text-blue-600">Geplant: {data.projected.fromSchedule.toFixed(1)}h</span>
              <span className="text-blue-800 font-medium">
                Erwarteter Saldo: {data.projected.expectedBalanceAfter > 0 ? '+' : ''}
                {data.projected.expectedBalanceAfter.toFixed(1)}h
              </span>
            </div>
          </div>
        )}

        {data.history.length > 0 && (
          <div>
            <h4 className="text-sm font-medium mb-2">Wochen-Historie</h4>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>KW</TableHead>
                  <TableHead>Geplant</TableHead>
                  <TableHead>Soll</TableHead>
                  <TableHead>Delta</TableHead>
                  <TableHead>Saldo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {[...data.history].reverse().map(entry => {
                  const deltaColor = entry.delta > 0 ? 'text-green-600' : entry.delta < 0 ? 'text-red-600' : '';
                  return (
                    <TableRow key={`${entry.year}-${entry.week}`}>
                      <TableCell className="font-medium">{entry.week}/{entry.year}</TableCell>
                      <TableCell>{entry.scheduledHours.toFixed(1)}h</TableCell>
                      <TableCell>{entry.contractHours.toFixed(1)}h</TableCell>
                      <TableCell className={deltaColor}>
                        {entry.delta > 0 ? '+' : ''}{entry.delta.toFixed(1)}h
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={balanceColor(entry.balance)}>
                          {entry.balance > 0 ? '+' : ''}{entry.balance.toFixed(1)}h
                        </Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}

        {data.history.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-4">
            Noch keine Zeitkonten-Historie vorhanden
          </p>
        )}
      </CardContent>
    </Card>
  );
}