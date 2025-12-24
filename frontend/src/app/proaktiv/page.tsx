'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import {
  getRiskRadar,
  getDeadlineStats,
  getProactiveAlerts,
  getDeadlines,
  snoozeProactiveAlert,
  dismissProactiveAlert,
  type RiskRadar,
  type DeadlineStats,
  type ProactiveAlert,
  type Deadline,
} from '@/lib/api/client';

// Severity badge colors (mapped to Badge variant)
const severityVariants: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
  info: 'info',
  low: 'default',
  medium: 'warning',
  high: 'warning',
  critical: 'danger',
};

// Risk score to color
function getRiskColor(score: number): string {
  if (score < 30) return 'text-green-600';
  if (score < 60) return 'text-yellow-600';
  if (score < 80) return 'text-orange-500';
  return 'text-red-600';
}

// Trend icon
function TrendIcon({ trend }: { trend: 'improving' | 'stable' | 'worsening' }) {
  if (trend === 'improving') {
    return <span className="text-green-500">&#8595;</span>;
  }
  if (trend === 'worsening') {
    return <span className="text-red-500">&#8593;</span>;
  }
  return <span className="text-gray-400">&#8212;</span>;
}

export default function ProaktivPage() {
  const { token } = useAuth();
  const [riskRadar, setRiskRadar] = useState<RiskRadar | null>(null);
  const [deadlineStats, setDeadlineStats] = useState<DeadlineStats | null>(null);
  const [alerts, setAlerts] = useState<ProactiveAlert[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      if (!token) return;

      try {
        setLoading(true);
        const [radar, stats, alertList, deadlineList] = await Promise.all([     
          getRiskRadar(token),
          getDeadlineStats(token),
          getProactiveAlerts(token, {
            status: ['new', 'seen', 'in_progress'],
            limit: 10,
          }),
          getDeadlines(token, { daysAhead: 30, includeOverdue: true }),
        ]);

        setRiskRadar(radar);
        setDeadlineStats(stats);
        setAlerts(alertList.items);
        setDeadlines(deadlineList);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Fehler beim Laden');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [token]);

  async function handleSnooze(alertId: string) {
    if (!token) return;
    try {
      await snoozeProactiveAlert(alertId, 3, token);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch {
      // Handle error silently for now
    }
  }

  async function handleDismiss(alertId: string) {
    if (!token) return;
    try {
      await dismissProactiveAlert(alertId, null, token);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch {
      // Handle error silently for now
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="h-48 bg-gray-200 rounded"></div>
            <div className="h-48 bg-gray-200 rounded"></div>
            <div className="h-48 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <Card className="p-6 bg-red-50 border-red-200">
          <p className="text-red-700">{error}</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Proaktiver AI-Jurist</h1>
        <p className="text-gray-600 mt-1">
          Ihr digitaler Rechtsberater denkt mit und warnt Sie rechtzeitig
        </p>
      </div>

      {/* Risk Radar Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Overall Risk Score */}
        <Card className="p-6">
          <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
            Gesamtrisiko
          </h2>
          <div className="mt-4 flex items-end gap-3">
            <span className={`text-5xl font-bold ${getRiskColor(riskRadar?.overall_score ?? 0)}`}>
              {riskRadar?.overall_score ?? 0}
            </span>
            <span className="text-gray-400 text-lg mb-1">/100</span>
            {riskRadar && (
              <span className="ml-auto text-sm">
                <TrendIcon trend={riskRadar.overall_trend} />
              </span>
            )}
          </div>
          <p className="mt-2 text-sm text-gray-500">
            {(riskRadar?.overall_score ?? 0) < 30
              ? 'Niedriges Risiko'
              : (riskRadar?.overall_score ?? 0) < 60
                ? 'Mittleres Risiko'
                : (riskRadar?.overall_score ?? 0) < 80
                  ? 'Erhöhtes Risiko'
                  : 'Kritisches Risiko'}
          </p>
        </Card>

        {/* Urgent Alerts */}
        <Card className="p-6">
          <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
            Dringende Alerts
          </h2>
          <div className="mt-4 flex items-end gap-3">
            <span className="text-5xl font-bold text-orange-500">
              {riskRadar?.urgent_alerts ?? 0}
            </span>
          </div>
          <p className="mt-2 text-sm text-gray-500">
            Handlungsbedarf
          </p>
        </Card>

        {/* Upcoming Deadlines */}
        <Card className="p-6">
          <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
            Fristen (30 Tage)
          </h2>
          <div className="mt-4 flex items-end gap-3">
            <span className="text-5xl font-bold text-blue-600">
              {deadlineStats?.upcoming_30_days ?? 0}
            </span>
            {(deadlineStats?.overdue ?? 0) > 0 && (
              <Badge variant="danger" className="mb-1">
                {deadlineStats?.overdue} überfällig
              </Badge>
            )}
          </div>
          <p className="mt-2 text-sm text-gray-500">
            davon {deadlineStats?.upcoming_7_days ?? 0} in 7 Tagen
          </p>
        </Card>
      </div>

      {/* Risk Categories */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Risk Radar</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {riskRadar?.categories.map((category) => (
            <div
              key={category.name}
              className="p-4 bg-gray-50 rounded-lg"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">{category.name}</span>
                <TrendIcon trend={category.trend} />
              </div>
              <div className="mt-2">
                <div className="flex items-end gap-2">
                  <span className={`text-2xl font-bold ${getRiskColor(category.score)}`}>
                    {category.score}
                  </span>
                  <span className="text-gray-400 text-sm mb-1">/100</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                  <div
                    className={`h-2 rounded-full ${
                      category.score < 30
                        ? 'bg-green-500'
                        : category.score < 60
                          ? 'bg-yellow-500'
                          : category.score < 80
                            ? 'bg-orange-500'
                            : 'bg-red-500'
                    }`}
                    style={{ width: `${category.score}%` }}
                  />
                </div>
              </div>
              <p className="mt-2 text-xs text-gray-500">
                {category.items_at_risk} von {category.total_items} kritisch
              </p>
              {category.key_issues.length > 0 && (
                <ul className="mt-2 text-xs text-gray-600">
                  {category.key_issues.slice(0, 2).map((issue, idx) => (
                    <li key={idx} className="truncate">• {issue}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Two Column Layout: Alerts and Deadlines */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Alerts */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Aktuelle Alerts</h2>
            <Link href="/proaktiv/alerts">
              <Button variant="ghost" size="sm">Alle anzeigen</Button>
            </Link>
          </div>

          {alerts.length === 0 ? (
            <p className="text-gray-500 text-sm">Keine offenen Alerts</p>
          ) : (
            <div className="space-y-3">
              {alerts.slice(0, 5).map((alert) => (
                <div
                  key={alert.id}
                  className="p-3 bg-gray-50 rounded-lg border border-gray-100"
                >
                  <div className="flex items-start gap-3">
                    <Badge variant={severityVariants[alert.severity] || 'gray'}>
                      {alert.severity}
                    </Badge>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 text-sm truncate">
                        {alert.title}
                      </p>
                      {alert.related_contract_filename && (
                        <p className="text-xs text-gray-500 truncate">
                          {alert.related_contract_filename}
                        </p>
                      )}
                      {alert.ai_recommendation && (
                        <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                          {alert.ai_recommendation}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="mt-2 flex gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleSnooze(alert.id)}
                    >
                      Später
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDismiss(alert.id)}
                    >
                      Ignorieren
                    </Button>
                    {alert.related_contract_id && (
                      <Link href={`/vertraege/${alert.related_contract_id}`}>
                        <Button size="sm" variant="secondary">
                          Vertrag
                        </Button>
                      </Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Deadlines */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Kommende Fristen</h2>
            <Link href="/proaktiv/fristen">
              <Button variant="ghost" size="sm">Alle anzeigen</Button>
            </Link>
          </div>

          {deadlines.length === 0 ? (
            <p className="text-gray-500 text-sm">Keine anstehenden Fristen</p>
          ) : (
            <div className="space-y-3">
              {deadlines.slice(0, 5).map((deadline) => (
                <div
                  key={deadline.id}
                  className={`p-3 rounded-lg border ${
                    deadline.is_overdue
                      ? 'bg-red-50 border-red-200'
                      : deadline.needs_attention
                        ? 'bg-yellow-50 border-yellow-200'
                        : 'bg-gray-50 border-gray-100'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 text-sm">
                        {deadline.deadline_type === 'termination_notice'
                          ? 'Kündigungsfrist'
                          : deadline.deadline_type === 'auto_renewal'
                            ? 'Auto-Verlängerung'
                            : deadline.deadline_type === 'payment_due'
                              ? 'Zahlung fällig'
                              : deadline.deadline_type === 'contract_end'
                                ? 'Vertragsende'
                                : deadline.deadline_type}
                      </p>
                      {deadline.contract_filename && (
                        <p className="text-xs text-gray-500 truncate">
                          {deadline.contract_filename}
                        </p>
                      )}
                    </div>
                    <div className="text-right">
                      <p className={`font-bold ${
                        deadline.is_overdue
                          ? 'text-red-600'
                          : deadline.days_until <= 7
                            ? 'text-orange-500'
                            : 'text-gray-700'
                      }`}>
                        {deadline.is_overdue
                          ? `${Math.abs(deadline.days_until)} Tage überfällig`
                          : `${deadline.days_until} Tage`}
                      </p>
                      <p className="text-xs text-gray-500">
                        {new Date(deadline.deadline_date).toLocaleDateString('de-AT')}
                      </p>
                    </div>
                  </div>
                  {deadline.source_clause && (
                    <p className="mt-2 text-xs text-gray-600 line-clamp-2 italic">
                      &quot;{deadline.source_clause}&quot;
                    </p>
                  )}
                  {!deadline.is_verified && (
                    <Badge variant="warning" className="mt-2">
                      AI-extrahiert ({Math.round(deadline.confidence * 100)}%)
                    </Badge>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Recommendations */}
      {riskRadar && riskRadar.recommendations.length > 0 && (
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Empfehlungen</h2>
          <ul className="space-y-2">
            {riskRadar.recommendations.map((rec, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-gray-400">•</span>
                <span className="text-gray-700">{rec}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
