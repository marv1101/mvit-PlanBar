import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Badge } from '../components/ui/badge';
import { Loader2, Clock, Pencil, ExternalLink } from 'lucide-react';
import { EmployeeTimeAccount } from '../types';
import { getAllTimeAccounts } from '../services/employeeService';
import { timeAccountFromResponse } from '../lib/mappers';
import { AdjustBalanceDialog } from '../components/AdjustBalanceDialog';

function balanceColor(balance: number): string {
  if (Math.abs(balance) <= 5) return 'text-green-600 bg-green-50 border-green-200';
  if (Math.abs(balance) <= 15) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
  return 'text-red-600 bg-red-50 border-red-200';
}

function BalanceBadge({ balance }: { balance: number }) {
  return (
    <Badge variant="outline" className={balanceColor(balance)}>
      {balance > 0 ? '+' : ''}{balance.toFixed(1)}h
    </Badge>
  );
}

export function TimeAccounts() {
  const [accounts, setAccounts] = useState<EmployeeTimeAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adjustTarget, setAdjustTarget] = useState<EmployeeTimeAccount | null>(null);
  const navigate = useNavigate();

  function load() {
    setLoading(true);
    setError(null);
    getAllTimeAccounts()
      .then(res => setAccounts(res.map(timeAccountFromResponse)))
      .catch(() => setError('Fehler beim Laden der Zeitkonten'))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="font-semibold text-2xl mb-2">Zeitkonten</h2>
          <p className="text-gray-600">Übersicht aller Mitarbeiter-Zeitkonten</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <Loader2 className="h-8 w-8 mx-auto text-blue-600 mb-4 animate-spin" />
            <p className="text-gray-600">Lade Zeitkonten...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="font-semibold text-2xl mb-2">Zeitkonten</h2>
          <p className="text-gray-600">Übersicht aller Mitarbeiter-Zeitkonten</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-red-600 mb-4">{error}</p>
            <Button onClick={load}>Erneut laden</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-semibold text-2xl mb-2">Zeitkonten</h2>
        <p className="text-gray-600">Übersicht aller Mitarbeiter-Zeitkonten</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Alle Zeitkonten
          </CardTitle>
          <CardDescription>{accounts.length} Mitarbeiter</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {accounts.length === 0 ? (
            <div className="py-12 text-center text-gray-500">
              Keine Zeitkonten-Daten vorhanden
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Mitarbeiter</TableHead>
                  <TableHead>Aktueller Saldo</TableHead>
                  <TableHead>Prognose</TableHead>
                  <TableHead className="w-24" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {accounts.map(acct => (
                  <TableRow key={acct.employeeId}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <button
                          className="font-medium text-blue-600 hover:underline hover:text-blue-800"
                          onClick={() => navigate(`/employee-view?employee=${acct.employeeId}`)}
                        >
                          {acct.employeeName}
                        </button>
                        <ExternalLink className="h-3 w-3 text-gray-400" />
                      </div>
                    </TableCell>
                    <TableCell>
                      <BalanceBadge balance={acct.currentBalance} />
                    </TableCell>
                    <TableCell>
                      {acct.projected ? (
                        <span className="text-sm text-gray-600">
                          {acct.projected.expectedBalanceAfter > 0 ? '+' : ''}
                          {acct.projected.expectedBalanceAfter.toFixed(1)}h
                        </span>
                      ) : (
                        <span className="text-sm text-gray-400">&ndash;</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setAdjustTarget(acct)}
                      >
                        <Pencil className="h-4 w-4 mr-1" />
                        Korrigieren
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {adjustTarget && (
        <AdjustBalanceDialog
          employeeId={adjustTarget.employeeId}
          employeeName={adjustTarget.employeeName}
          currentBalance={adjustTarget.currentBalance}
          onClose={() => setAdjustTarget(null)}
          onSaved={() => {
            setAdjustTarget(null);
            load();
          }}
        />
      )}
    </div>
  );
}
