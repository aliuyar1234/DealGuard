'use client';

import { RiskScore } from '@/components/contracts/RiskScore';
import { Shell } from '@/components/layout/Shell';
import { Badge, Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { useAuth } from '@/hooks/useAuth';
import { useContracts } from '@/hooks/useContracts';
import { Contract } from '@/lib/api/client';
import {
  formatDate,
  formatFileSize,
  getCategoryLabel,
  getContractTypeLabel,
  getSeverityLabel,
  getStatusLabel,
} from '@/lib/utils';
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Download,
  FileText,
  Info,
  Lightbulb,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

export default function ContractDetailPage() {
  const params = useParams();
  const router = useRouter();
  const contractId = params.id as string;
  const { token, loading: authLoading } = useAuth();
  const { fetchContract, analyze, loading, error } = useContracts();
  const [contract, setContract] = useState<Contract | null>(null);
  const [expandedFindings, setExpandedFindings] = useState<Set<string>>(new Set());
  const [polling, setPolling] = useState(false);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !token) {
      router.push('/login');
    }
  }, [authLoading, token, router]);

  // Fetch contract data
  const loadContract = useCallback(async () => {
    if (!token || !contractId) return;
    const data = await fetchContract(contractId, token);
    if (data) {
      setContract(data);
      // Poll if still processing
      if (data.status === 'processing' || data.status === 'pending') {
        setPolling(true);
      } else {
        setPolling(false);
      }
    }
  }, [token, contractId, fetchContract]);

  useEffect(() => {
    loadContract();
  }, [loadContract]);

  // Polling for processing status
  useEffect(() => {
    if (!polling) return;
    const interval = setInterval(() => {
      loadContract();
    }, 3000);
    return () => clearInterval(interval);
  }, [polling, loadContract]);

  // Trigger analysis manually
  const handleAnalyze = async () => {
    if (!token || !contractId) return;
    try {
      const result = await analyze(contractId, token);
      setContract(result);
      setPolling(result.status === 'processing');
    } catch {
      // Error handled by hook
    }
  };

  const toggleFinding = (id: string) => {
    const newExpanded = new Set(expandedFindings);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedFindings(newExpanded);
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return <AlertTriangle className="w-5 h-5 text-red-500" />;
      case 'medium':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case 'low':
        return <Info className="w-5 h-5 text-blue-500" />;
      default:
        return <Info className="w-5 h-5 text-gray-500" />;
    }
  };

  const getSeverityBadgeVariant = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'danger';
      case 'high':
        return 'danger';
      case 'medium':
        return 'warning';
      case 'low':
        return 'info';
      default:
        return 'default';
    }
  };

  // Show loading while checking auth or loading contract
  if (authLoading || (loading && !contract)) {
    return (
      <Shell>
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        </div>
      </Shell>
    );
  }

  // Show error if contract not found
  if (error && !contract) {
    return (
      <Shell>
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center space-x-4 mb-6">
            <Link href="/vertraege">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Zurück
              </Button>
            </Link>
          </div>
          <Card>
            <CardContent className="py-12 text-center">
              <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Vertrag nicht gefunden
              </h3>
              <p className="text-gray-500 mb-4">{error}</p>
              <Link href="/vertraege">
                <Button>Zur Übersicht</Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </Shell>
    );
  }

  // No contract yet
  if (!contract) {
    return (
      <Shell>
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        </div>
      </Shell>
    );
  }

  return (
    <Shell>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link href="/vertraege">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Zurück
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {contract.filename}
              </h1>
              <div className="flex items-center space-x-3 mt-1 text-sm text-gray-500">
                <span>{formatFileSize(contract.file_size_bytes)}</span>
                <span>•</span>
                <span>{contract.page_count || '?'} Seiten</span>
                {contract.contract_type && (
                  <>
                    <span>•</span>
                    <span>{getContractTypeLabel(contract.contract_type)}</span>
                  </>
                )}
                <span>•</span>
                <span>{formatDate(contract.created_at)}</span>
              </div>
            </div>
          </div>
          <Button variant="secondary">
            <Download className="w-4 h-4 mr-2" />
            Download
          </Button>
        </div>

        {/* Processing status */}
        {(contract.status === 'processing' || contract.status === 'pending') && (
          <Card>
            <CardContent className="py-8">
              <div className="flex flex-col items-center justify-center text-center">
                <Loader2 className="w-12 h-12 animate-spin text-primary-600 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {contract.status === 'pending' ? 'Warte auf Analyse...' : 'Vertrag wird analysiert...'}
                </h3>
                <p className="text-gray-500">
                  Die KI-Analyse kann einige Sekunden dauern. Diese Seite aktualisiert sich automatisch.
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Failed status */}
        {contract.status === 'failed' && (
          <Card>
            <CardContent className="py-8">
              <div className="flex flex-col items-center justify-center text-center">
                <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Analyse fehlgeschlagen
                </h3>
                <p className="text-gray-500 mb-4">
                  Bei der Analyse ist ein Fehler aufgetreten. Bitte versuchen Sie es erneut.
                </p>
                <Button onClick={handleAnalyze} disabled={loading}>
                  {loading ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4 mr-2" />
                  )}
                  Erneut analysieren
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Risk Score Overview */}
        {contract.analysis && (
          <Card>
            <CardContent className="py-6">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h2 className="text-lg font-semibold text-gray-900 mb-3">
                    Risikoanalyse
                  </h2>
                  <p className="text-gray-600">{contract.analysis.summary}</p>
                </div>
                <div className="ml-8">
                  <RiskScore
                    score={contract.analysis.risk_score}
                    level={contract.analysis.risk_level}
                    size="lg"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Recommendations */}
        {contract.analysis && contract.analysis.recommendations.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Lightbulb className="w-5 h-5 mr-2 text-yellow-500" />
                Empfehlungen
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {contract.analysis.recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start">
                    <CheckCircle className="w-5 h-5 text-primary-600 mr-3 mt-0.5 flex-shrink-0" />
                    <span className="text-gray-700">{rec}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* Findings */}
        {contract.analysis && contract.analysis.findings.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>
                Erkannte Risiken ({contract.analysis.findings.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-gray-200">
                {contract.analysis.findings.map((finding) => (
                  <div key={finding.id} className="p-4">
                    {/* Finding header */}
                    <button
                      onClick={() => toggleFinding(finding.id)}
                      className="w-full flex items-center justify-between text-left"
                    >
                      <div className="flex items-center space-x-3">
                        {getSeverityIcon(finding.severity)}
                        <div>
                          <div className="flex items-center space-x-2">
                            <h3 className="font-medium text-gray-900">
                              {finding.title}
                            </h3>
                            <Badge
                              variant={getSeverityBadgeVariant(finding.severity) as any}
                            >
                              {getSeverityLabel(finding.severity)}
                            </Badge>
                            <Badge variant="default">
                              {getCategoryLabel(finding.category)}
                            </Badge>
                          </div>
                          {finding.clause_location && (
                            <p className="text-sm text-gray-500 mt-1">
                              {finding.clause_location.paragraph}, Seite{' '}
                              {finding.clause_location.page}
                            </p>
                          )}
                        </div>
                      </div>
                      {expandedFindings.has(finding.id) ? (
                        <ChevronUp className="w-5 h-5 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                      )}
                    </button>

                    {/* Finding details */}
                    {expandedFindings.has(finding.id) && (
                      <div className="mt-4 pl-8 space-y-4">
                        {/* Description */}
                        <div>
                          <h4 className="text-sm font-medium text-gray-700 mb-1">
                            Erklärung
                          </h4>
                          <p className="text-gray-600">{finding.description}</p>
                        </div>

                        {/* Original clause */}
                        {finding.original_clause_text && (
                          <div>
                            <h4 className="text-sm font-medium text-gray-700 mb-1">
                              Originaltext
                            </h4>
                            <blockquote className="bg-gray-50 border-l-4 border-gray-300 p-3 text-sm text-gray-600 italic">
                              {finding.original_clause_text}
                            </blockquote>
                          </div>
                        )}

                        {/* Suggested change */}
                        {finding.suggested_change && (
                          <div>
                            <h4 className="text-sm font-medium text-gray-700 mb-1">
                              Empfohlene Änderung
                            </h4>
                            <p className="text-gray-600 bg-green-50 border-l-4 border-green-400 p-3">
                              {finding.suggested_change}
                            </p>
                          </div>
                        )}

                        {/* Market comparison */}
                        {finding.market_comparison && (
                          <div>
                            <h4 className="text-sm font-medium text-gray-700 mb-1">
                              Marktvergleich
                            </h4>
                            <p className="text-gray-600">
                              {finding.market_comparison}
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Meta info */}
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between text-sm text-gray-500">
              <div className="flex items-center space-x-4">
                <span>
                  Analysiert am {formatDate(contract.analysis?.created_at || '')}
                </span>
                {contract.analysis && (
                  <>
                    <span>•</span>
                    <span>
                      Dauer: {(contract.analysis.processing_time_ms / 1000).toFixed(1)}s
                    </span>
                  </>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </Shell>
  );
}
