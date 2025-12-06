'use client';

import { Shell } from '@/components/layout/Shell';
import { Badge, Button, Card, CardContent, CardHeader, useToast } from '@/components/ui';
import { RiskScore } from '@/components/contracts/RiskScore';
import { useAuth } from '@/hooks/useAuth';
import { usePartner } from '@/hooks/usePartners';
import { formatDate } from '@/lib/utils';
import {
  AlertCircle,
  ArrowLeft,
  Building2,
  CheckCircle,
  Clock,
  Eye,
  EyeOff,
  ExternalLink,
  FileText,
  Loader2,
  Mail,
  MapPin,
  Phone,
  Play,
  RefreshCw,
  Shield,
  Trash2,
  XCircle,
} from 'lucide-react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';

const PARTNER_TYPE_LABELS: Record<string, string> = {
  supplier: 'Lieferant',
  customer: 'Kunde',
  service_provider: 'Dienstleister',
  distributor: 'Distributor',
  partner: 'Partner',
  other: 'Sonstige',
};

const CHECK_TYPE_LABELS: Record<string, string> = {
  handelsregister: 'Handelsregister',
  credit_check: 'Bonität',
  sanctions: 'Sanktionen',
  insolvency: 'Insolvenz',
  news: 'News',
  esg: 'ESG',
  manual: 'Manuell',
};

const ALERT_TYPE_LABELS: Record<string, string> = {
  insolvency: 'Insolvenz',
  management_change: 'Geschäftsführerwechsel',
  address_change: 'Adressänderung',
  credit_downgrade: 'Bonität verschlechtert',
  sanction_hit: 'Sanktionstreffer',
  negative_news: 'Negative Nachrichten',
  legal_issue: 'Rechtliches Problem',
  financial_warning: 'Finanzwarnung',
};

export default function PartnerDetailPage() {
  const params = useParams();
  const router = useRouter();
  const partnerId = params.id as string;
  const { token, loading: authLoading } = useAuth();
  const { partner, loading, error, checkLoading, fetchPartner, runChecks, update, remove } = usePartner();
  const { addToast } = useToast();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !token) {
      router.push('/login');
    }
  }, [authLoading, token, router]);

  // Fetch partner when token is available
  useEffect(() => {
    if (token && partnerId) {
      fetchPartner(partnerId, token);
    }
  }, [token, partnerId, fetchPartner]);

  const handleRunChecks = async () => {
    if (!token) return;
    const checks = await runChecks(partnerId, token);
    if (checks.length > 0) {
      addToast('success', `${checks.length} Checks erfolgreich durchgeführt`);
    }
  };

  const handleToggleWatch = async () => {
    if (!token || !partner) return;
    const updated = await update(partnerId, { is_watched: !partner.is_watched }, token);
    if (updated) {
      addToast(
        'success',
        updated.is_watched ? 'Partner zur Watchlist hinzugefügt' : 'Partner von Watchlist entfernt'
      );
    }
  };

  const handleDelete = async () => {
    if (!token) return;
    if (!confirm('Partner wirklich löschen?')) return;
    const success = await remove(partnerId, token);
    if (success) {
      addToast('success', 'Partner gelöscht');
      router.push('/partner');
    }
  };

  // Show loading while checking auth or fetching partner
  if (authLoading || loading) {
    return (
      <Shell>
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        </div>
      </Shell>
    );
  }

  if (error) {
    return (
      <Shell>
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-600">{error}</p>
        </div>
      </Shell>
    );
  }

  if (!partner) {
    return (
      <Shell>
        <div className="text-center py-12">
          <Building2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Partner nicht gefunden</h2>
          <Link href="/partner">
            <Button variant="secondary">Zurück zur Übersicht</Button>
          </Link>
        </div>
      </Shell>
    );
  }

  return (
    <Shell>
      <div className="space-y-6">
        {/* Back link */}
        <Link
          href="/partner"
          className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Zurück zur Übersicht
        </Link>

        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-gray-100 rounded-lg">
              <Building2 className="w-10 h-10 text-gray-600" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-2xl font-bold text-gray-900">{partner.name}</h1>
                {partner.is_watched && (
                  <Badge variant="info" className="flex items-center space-x-1">
                    <Eye className="w-3 h-3" />
                    <span>Watchlist</span>
                  </Badge>
                )}
              </div>
              <div className="flex items-center space-x-3 mt-1 text-gray-500">
                <span>{PARTNER_TYPE_LABELS[partner.partner_type] || partner.partner_type}</span>
                {partner.city && (
                  <>
                    <span>•</span>
                    <span>{partner.city}</span>
                  </>
                )}
                {partner.handelsregister_id && (
                  <>
                    <span>•</span>
                    <span>{partner.handelsregister_id}</span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center space-x-2">
            <Button
              variant="secondary"
              onClick={handleToggleWatch}
              title={partner.is_watched ? 'Von Watchlist entfernen' : 'Zur Watchlist hinzufügen'}
            >
              {partner.is_watched ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </Button>
            <Button
              onClick={handleRunChecks}
              disabled={checkLoading}
            >
              {checkLoading ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <RefreshCw className="w-4 h-4 mr-2" />
              )}
              Checks ausführen
            </Button>
            <Button variant="danger" onClick={handleDelete}>
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Main content grid */}
        <div className="grid grid-cols-3 gap-6">
          {/* Left column - Risk & Checks */}
          <div className="col-span-2 space-y-6">
            {/* Risk Score */}
            <Card>
              <CardHeader>
                <h2 className="text-lg font-semibold flex items-center">
                  <Shield className="w-5 h-5 mr-2 text-primary-600" />
                  Risikobewertung
                </h2>
              </CardHeader>
              <CardContent>
                {partner.risk_score !== null ? (
                  <div className="flex items-center space-x-8">
                    <RiskScore score={partner.risk_score} level={(partner.risk_level === 'unknown' ? 'low' : partner.risk_level) || 'low'} size="lg" />
                    <div className="flex-1">
                      <p className="text-gray-600">
                        {partner.risk_level === 'low' && 'Niedriges Risiko - Partner erscheint zuverlässig.'}
                        {partner.risk_level === 'medium' && 'Mittleres Risiko - Einzelne Auffälligkeiten vorhanden.'}
                        {partner.risk_level === 'high' && 'Hohes Risiko - Mehrere Warnsignale erkannt.'}
                        {partner.risk_level === 'critical' && 'Kritisches Risiko - Dringende Prüfung empfohlen!'}
                      </p>
                      {partner.last_check_at && (
                        <p className="text-sm text-gray-400 mt-2">
                          Letzte Prüfung: {formatDate(partner.last_check_at)}
                        </p>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Shield className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-500 mb-4">Noch keine Risikobewertung vorhanden</p>
                    <Button onClick={handleRunChecks} disabled={checkLoading}>
                      {checkLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      ) : (
                        <Play className="w-4 h-4 mr-2" />
                      )}
                      Jetzt prüfen
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Checks */}
            {partner.checks && partner.checks.length > 0 && (
              <Card>
                <CardHeader>
                  <h2 className="text-lg font-semibold">Durchgeführte Checks</h2>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {partner.checks.map((check) => (
                      <div
                        key={check.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                      >
                        <div className="flex items-center space-x-3">
                          {check.status === 'completed' ? (
                            <CheckCircle className="w-5 h-5 text-green-500" />
                          ) : check.status === 'failed' ? (
                            <XCircle className="w-5 h-5 text-red-500" />
                          ) : (
                            <Clock className="w-5 h-5 text-yellow-500" />
                          )}
                          <div>
                            <p className="font-medium text-gray-900">
                              {CHECK_TYPE_LABELS[check.check_type] || check.check_type}
                            </p>
                            {check.result_summary && (
                              <p className="text-sm text-gray-500">{check.result_summary}</p>
                            )}
                          </div>
                        </div>
                        <div className="text-right">
                          {check.score !== null && (
                            <span className={`text-lg font-bold ${
                              check.score <= 30 ? 'text-green-600' :
                              check.score <= 60 ? 'text-yellow-600' :
                              'text-red-600'
                            }`}>
                              {check.score}
                            </span>
                          )}
                          <p className="text-xs text-gray-400">
                            {formatDate(check.created_at)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Alerts */}
            {partner.alerts && partner.alerts.length > 0 && (
              <Card>
                <CardHeader>
                  <h2 className="text-lg font-semibold text-orange-600">Warnungen</h2>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {partner.alerts.filter(a => !a.is_dismissed).map((alert) => (
                      <div
                        key={alert.id}
                        className={`p-3 rounded-lg border ${
                          alert.severity === 'critical' ? 'bg-red-50 border-red-200' :
                          alert.severity === 'warning' ? 'bg-yellow-50 border-yellow-200' :
                          'bg-blue-50 border-blue-200'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-medium">
                              {ALERT_TYPE_LABELS[alert.alert_type] || alert.alert_type}: {alert.title}
                            </p>
                            <p className="text-sm text-gray-600 mt-1">{alert.description}</p>
                            {alert.source_url && (
                              <a
                                href={alert.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center text-sm text-primary-600 hover:underline mt-2"
                              >
                                Quelle <ExternalLink className="w-3 h-3 ml-1" />
                              </a>
                            )}
                          </div>
                          <Badge
                            variant={
                              alert.severity === 'critical' ? 'danger' :
                              alert.severity === 'warning' ? 'warning' :
                              'info'
                            }
                          >
                            {alert.severity}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Linked Contracts */}
            {partner.contracts && partner.contracts.length > 0 && (
              <Card>
                <CardHeader>
                  <h2 className="text-lg font-semibold">Verknüpfte Verträge</h2>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {partner.contracts.map((link) => (
                      <Link
                        key={link.id}
                        href={`/vertraege/${link.contract_id}`}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                      >
                        <div className="flex items-center space-x-3">
                          <FileText className="w-5 h-5 text-gray-400" />
                          <div>
                            <p className="font-medium text-gray-900">
                              {link.contract_filename || 'Vertrag'}
                            </p>
                            {link.role && (
                              <p className="text-sm text-gray-500">Rolle: {link.role}</p>
                            )}
                          </div>
                        </div>
                        <span className="text-sm text-gray-400">
                          {formatDate(link.created_at)}
                        </span>
                      </Link>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right column - Info */}
          <div className="space-y-6">
            {/* Contact */}
            <Card>
              <CardHeader>
                <h2 className="text-lg font-semibold">Kontakt</h2>
              </CardHeader>
              <CardContent className="space-y-4">
                {(partner.street || partner.city) && (
                  <div className="flex items-start space-x-3">
                    <MapPin className="w-5 h-5 text-gray-400 mt-0.5" />
                    <div>
                      {partner.street && <p>{partner.street}</p>}
                      <p>
                        {partner.postal_code} {partner.city}
                      </p>
                      <p>{partner.country}</p>
                    </div>
                  </div>
                )}
                {partner.email && (
                  <div className="flex items-center space-x-3">
                    <Mail className="w-5 h-5 text-gray-400" />
                    <a href={`mailto:${partner.email}`} className="text-primary-600 hover:underline">
                      {partner.email}
                    </a>
                  </div>
                )}
                {partner.phone && (
                  <div className="flex items-center space-x-3">
                    <Phone className="w-5 h-5 text-gray-400" />
                    <a href={`tel:${partner.phone}`} className="text-primary-600 hover:underline">
                      {partner.phone}
                    </a>
                  </div>
                )}
                {partner.website && (
                  <div className="flex items-center space-x-3">
                    <ExternalLink className="w-5 h-5 text-gray-400" />
                    <a
                      href={partner.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 hover:underline"
                    >
                      Website
                    </a>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* IDs */}
            <Card>
              <CardHeader>
                <h2 className="text-lg font-semibold">Kennzahlen</h2>
              </CardHeader>
              <CardContent className="space-y-3">
                {partner.handelsregister_id && (
                  <div>
                    <p className="text-sm text-gray-500">Handelsregister</p>
                    <p className="font-mono">{partner.handelsregister_id}</p>
                  </div>
                )}
                {partner.vat_id && (
                  <div>
                    <p className="text-sm text-gray-500">USt-IdNr.</p>
                    <p className="font-mono">{partner.vat_id}</p>
                  </div>
                )}
                {partner.tax_id && (
                  <div>
                    <p className="text-sm text-gray-500">Steuernummer</p>
                    <p className="font-mono">{partner.tax_id}</p>
                  </div>
                )}
                {!partner.handelsregister_id && !partner.vat_id && !partner.tax_id && (
                  <p className="text-gray-400 text-sm">Keine Kennzahlen hinterlegt</p>
                )}
              </CardContent>
            </Card>

            {/* Notes */}
            {partner.notes && (
              <Card>
                <CardHeader>
                  <h2 className="text-lg font-semibold">Notizen</h2>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600 whitespace-pre-wrap">{partner.notes}</p>
                </CardContent>
              </Card>
            )}

            {/* Meta */}
            <Card>
              <CardContent className="py-4">
                <p className="text-sm text-gray-500">
                  Erstellt am {formatDate(partner.created_at)}
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </Shell>
  );
}
