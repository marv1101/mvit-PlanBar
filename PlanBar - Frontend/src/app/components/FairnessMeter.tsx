import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, ReferenceLine, CartesianGrid } from 'recharts';
import { Employee, Role, EmployeeFairnessEntry } from '../types';

interface FairnessMeterProps {
  employees: Employee[];
  roles: Role[];
  employeeFairness: Record<string, EmployeeFairnessEntry> | undefined;
}

interface ChartDataItem {
  name: string;
  employeeId: string;
  roleColor: string;
  plannedHours: number;
  contractHours: number;
  deviation: number;
  deviationType: string;
  projectedBalance: number;
  currentBalance: number;
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ payload: ChartDataItem }>; label?: string }) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border rounded-lg shadow-lg p-3 text-sm space-y-1">
      <p className="font-semibold">{d.name}</p>
      <p>Geplant: <span className="font-medium">{d.plannedHours.toFixed(1)}h</span></p>
      <p>Vertrag: <span className="font-medium">{d.contractHours.toFixed(1)}h</span></p>
      <p>
        Abweichung:{' '}
        <span className={Math.abs(d.deviation) > 10 ? 'text-red-600 font-medium' : 'text-green-600 font-medium'}>
          {d.deviation > 0 ? '+' : ''}{d.deviation.toFixed(1)}%
        </span>
      </p>
      <p>Saldo: <span className="font-medium">{d.currentBalance > 0 ? '+' : ''}{d.currentBalance.toFixed(1)}h</span></p>
      <p>Prognose-Saldo: <span className="font-medium">{d.projectedBalance > 0 ? '+' : ''}{d.projectedBalance.toFixed(1)}h</span></p>
    </div>
  );
}

function normalizeEmpId(empId: string): string {
  const match = empId.match(/^emp_(\d+)$/);
  if (match) return String(Number(match[1]));
  return empId;
}

export function FairnessMeter({ employees, roles, employeeFairness }: FairnessMeterProps) {
  if (!employeeFairness || Object.keys(employeeFairness).length === 0) return null;

  const chartData: ChartDataItem[] = Object.entries(employeeFairness).map(([empId, entry]) => {
    const normalizedId = normalizeEmpId(empId);
    const emp = employees.find(e => e.id === normalizedId);
    const empRole = emp?.roles?.[0];
    const role = roles.find(r => r.id === empRole);
    const plannedHours = entry.scheduledHours;
    const contractHours = entry.targetHours;
    const deviationPercent = contractHours > 0
      ? ((plannedHours - contractHours) / contractHours) * 100
      : 0;

    return {
      name: emp?.name || `MA #${empId}`,
      employeeId: empId,
      roleColor: role?.color || '#6b7280',
      plannedHours: Math.round(plannedHours * 10) / 10,
      contractHours: Math.round(contractHours * 10) / 10,
      deviation: Math.round(deviationPercent * 10) / 10,
      deviationType: deviationPercent > 10 ? 'over' : deviationPercent < -10 ? 'under' : 'equal',
      projectedBalance: Math.round(entry.projectedBalance * 10) / 10,
      currentBalance: Math.round(entry.currentBalanceHours * 10) / 10,
    };
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-purple-500" />
          <CardTitle>Fairness-Meter</CardTitle>
        </div>
        <CardDescription>Geplante Stunden vs. Vertragsstunden pro Mitarbeiter (nach Skill-Gruppen)</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 50)}>
          <BarChart
            data={chartData}
            layout="vertical"
            barSize={20}
            barGap={4}
            margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" unit="h" />
            <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 12 }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <ReferenceLine x={0} stroke="#666" />
            <Bar dataKey="plannedHours" fill="#3b82f6" name="Geplant" radius={[0, 4, 4, 0]} />
            <Bar dataKey="contractHours" fill="#22c55e" name="Vertrag" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>

        <div className="flex items-center gap-4 mt-4 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-blue-500" /> Geplante Stunden
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-green-500" /> Vertragsstunden (soll)
          </span>
          <span className="flex items-center gap-1 text-red-600">
            ⚠ Abweichung &gt;10%
          </span>
        </div>
      </CardContent>
    </Card>
  );
}