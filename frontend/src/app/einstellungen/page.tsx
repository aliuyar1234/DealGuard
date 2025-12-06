'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import {
  getSettings,
  updateAPIKeys,
  checkAIConnection,
  type SettingsResponse,
  type AIConnectionStatus,
} from '@/lib/api/client';
import {
  Key,
  Check,
  X,
  Loader2,
  AlertTriangle,
  ExternalLink,
  Zap,
} from 'lucide-react';

export default function EinstellungenPage() {
  const { token } = useAuth();
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<AIConnectionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [anthropicKey, setAnthropicKey] = useState('');
  const [deepseekKey, setDeepseekKey] = useState('');
  const [aiProvider, setAiProvider] = useState<'anthropic' | 'deepseek'>('anthropic');

  useEffect(() => {
    async function loadSettings() {
      if (!token) return;

      try {
        const data = await getSettings(token);
        setSettings(data);
        setAiProvider(data.api_keys.ai_provider);
      } catch (err) {
        setError('Fehler beim Laden der Einstellungen');
      } finally {
        setLoading(false);
      }
    }

    loadSettings();
  }, [token]);

  async function handleSave() {
    if (!token) return;

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const updates: { anthropic_api_key?: string; deepseek_api_key?: string; ai_provider?: 'anthropic' | 'deepseek' } = {
        ai_provider: aiProvider,
      };

      if (anthropicKey) {
        updates.anthropic_api_key = anthropicKey;
      }
      if (deepseekKey) {
        updates.deepseek_api_key = deepseekKey;
      }

      const result = await updateAPIKeys(updates, token);

      setSettings((prev) =>
        prev
          ? {
              ...prev,
              api_keys: result,
            }
          : null
      );

      setAnthropicKey('');
      setDeepseekKey('');
      setSuccess('Einstellungen gespeichert!');
      setTestResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Speichern');
    } finally {
      setSaving(false);
    }
  }

  async function handleTestConnection() {
    if (!token) return;

    setTesting(true);
    setTestResult(null);

    try {
      const result = await checkAIConnection(token);
      setTestResult(result);
    } catch (err) {
      setTestResult({
        status: 'error',
        message: err instanceof Error ? err.message : 'Verbindungstest fehlgeschlagen',
      });
    } finally {
      setTesting(false);
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8 max-w-3xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Einstellungen</h1>
        <p className="text-gray-600 mt-1">
          Verwalten Sie Ihre API-Keys und Systemeinstellungen
        </p>
      </div>

      {/* Status Banner */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
          <AlertTriangle className="w-5 h-5" />
          {error}
        </div>
      )}

      {success && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-green-700">
          <Check className="w-5 h-5" />
          {success}
        </div>
      )}

      {/* AI Provider Selection */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">AI Provider</h2>

        <div className="space-y-4">
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="ai_provider"
                value="anthropic"
                checked={aiProvider === 'anthropic'}
                onChange={(e) => setAiProvider(e.target.value as 'anthropic' | 'deepseek')}
                className="w-4 h-4 text-primary-600"
              />
              <span className="font-medium">Anthropic (Claude)</span>
              <Badge variant="info">Empfohlen</Badge>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="ai_provider"
                value="deepseek"
                checked={aiProvider === 'deepseek'}
                onChange={(e) => setAiProvider(e.target.value as 'anthropic' | 'deepseek')}
                className="w-4 h-4 text-primary-600"
              />
              <span className="font-medium">DeepSeek</span>
              <Badge variant="default">Günstig</Badge>
            </label>
          </div>

          <p className="text-sm text-gray-500">
            {aiProvider === 'anthropic'
              ? 'Claude ist der empfohlene Provider für beste Qualität bei Rechtsanalysen.'
              : 'DeepSeek ist günstiger (~$0.05/Analyse), aber weniger zuverlässig für komplexe Rechtsfragen.'}
          </p>
        </div>
      </Card>

      {/* API Keys */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">API Keys</h2>
          <div className="flex gap-2">
            {settings?.api_keys.anthropic_configured && (
              <Badge variant="success">Anthropic konfiguriert</Badge>
            )}
            {settings?.api_keys.deepseek_configured && (
              <Badge variant="success">DeepSeek konfiguriert</Badge>
            )}
          </div>
        </div>

        <div className="space-y-6">
          {/* Anthropic */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Anthropic API Key
              {settings?.api_keys.anthropic_configured && (
                <Check className="inline w-4 h-4 text-green-500 ml-2" />
              )}
            </label>
            <div className="flex gap-2">
              <Input
                type="password"
                placeholder={
                  settings?.api_keys.anthropic_configured
                    ? '••••••••••••••••••••'
                    : 'sk-ant-...'
                }
                value={anthropicKey}
                onChange={(e) => setAnthropicKey(e.target.value)}
                className="flex-1"
              />
              <a
                href="https://console.anthropic.com/settings/keys"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Erstellen Sie einen API Key unter{' '}
              <a
                href="https://console.anthropic.com/settings/keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:underline"
              >
                console.anthropic.com
              </a>
            </p>
          </div>

          {/* DeepSeek */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              DeepSeek API Key
              {settings?.api_keys.deepseek_configured && (
                <Check className="inline w-4 h-4 text-green-500 ml-2" />
              )}
            </label>
            <div className="flex gap-2">
              <Input
                type="password"
                placeholder={
                  settings?.api_keys.deepseek_configured
                    ? '••••••••••••••••••••'
                    : 'sk-...'
                }
                value={deepseekKey}
                onChange={(e) => setDeepseekKey(e.target.value)}
                className="flex-1"
              />
              <a
                href="https://platform.deepseek.com/api_keys"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Erstellen Sie einen API Key unter{' '}
              <a
                href="https://platform.deepseek.com/api_keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:underline"
              >
                platform.deepseek.com
              </a>
            </p>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <Button variant="secondary" onClick={handleTestConnection} disabled={testing}>
            {testing ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Teste...
              </>
            ) : (
              <>
                <Zap className="w-4 h-4 mr-2" />
                Verbindung testen
              </>
            )}
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Speichern...
              </>
            ) : (
              <>
                <Key className="w-4 h-4 mr-2" />
                Speichern
              </>
            )}
          </Button>
        </div>

        {/* Test Result */}
        {testResult && (
          <div
            className={`mt-4 p-4 rounded-lg ${
              testResult.status === 'ok'
                ? 'bg-green-50 border border-green-200 text-green-700'
                : 'bg-red-50 border border-red-200 text-red-700'
            }`}
          >
            <div className="flex items-center gap-2">
              {testResult.status === 'ok' ? (
                <Check className="w-5 h-5" />
              ) : (
                <X className="w-5 h-5" />
              )}
              <span className="font-medium">{testResult.message}</span>
            </div>
            {testResult.model && (
              <p className="mt-1 text-sm">Model: {testResult.model}</p>
            )}
          </div>
        )}
      </Card>

      {/* System Info */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">System-Info</h2>

        <dl className="space-y-3">
          <div className="flex justify-between">
            <dt className="text-gray-600">Version</dt>
            <dd className="font-medium">{settings?.app_version || '2.0.0'}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-600">Modus</dt>
            <dd className="font-medium">
              {settings?.single_tenant_mode ? 'Self-Hosted (Single-Tenant)' : 'Multi-Tenant'}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-600">Aktiver AI Provider</dt>
            <dd className="font-medium">
              {settings?.api_keys.ai_provider === 'anthropic' ? 'Anthropic Claude' : 'DeepSeek'}
            </dd>
          </div>
        </dl>
      </Card>

      {/* Data Sources Info */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Datenquellen</h2>
        <p className="text-sm text-gray-600 mb-4">
          DealGuard hat Zugang zu folgenden österreichischen und internationalen Datenquellen:
        </p>

        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium">RIS (Rechtsinformationssystem)</p>
              <p className="text-sm text-gray-500">Alle Bundesgesetze, OGH-Urteile - kostenlos</p>
            </div>
            <Badge variant="success">Aktiv</Badge>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium">Ediktsdatei</p>
              <p className="text-sm text-gray-500">Insolvenzen, Zwangsversteigerungen - kostenlos</p>
            </div>
            <Badge variant="success">Aktiv</Badge>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium">OpenFirmenbuch</p>
              <p className="text-sm text-gray-500">Firmendaten aus österreichischem Firmenbuch - kostenlos</p>
            </div>
            <Badge variant="success">Aktiv</Badge>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium">OpenSanctions</p>
              <p className="text-sm text-gray-500">EU/UN/US Sanktionslisten, PEP-Screening - kostenlos</p>
            </div>
            <Badge variant="success">Aktiv</Badge>
          </div>
        </div>
      </Card>
    </div>
  );
}
