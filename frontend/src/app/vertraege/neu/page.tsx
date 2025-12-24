'use client';

import { FileUpload } from '@/components/contracts/FileUpload';
import { Shell } from '@/components/layout/Shell';
import { Button, Card, CardContent, CardHeader, CardTitle, useToast } from '@/components/ui';
import { useAuth } from '@/hooks/useAuth';
import { useContracts } from '@/hooks/useContracts';
import { AlertCircle, ArrowLeft, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

const contractTypes = [
  { value: 'supplier', label: 'Lieferantenvertrag' },
  { value: 'customer', label: 'Kundenvertrag / AGB' },
  { value: 'service', label: 'Dienstleistungsvertrag' },
  { value: 'nda', label: 'Geheimhaltungsvereinbarung (NDA)' },
  { value: 'lease', label: 'Mietvertrag (Gewerbe)' },
  { value: 'employment', label: 'Arbeitsvertrag' },
  { value: 'license', label: 'Lizenzvertrag' },
  { value: 'other', label: 'Sonstiges' },
];

export default function NewContractPage() {
  const router = useRouter();
  const { token, loading: authLoading } = useAuth();
  const { upload, loading, error, clearError } = useContracts();
  const { addToast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [contractType, setContractType] = useState<string>('');

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !token) {
      router.push('/login');
    }
  }, [authLoading, token, router]);

  const handleUpload = async () => {
    if (!file || !token) return;

    clearError();

    try {
      const response = await upload(file, token, contractType || undefined);
      addToast('success', 'Vertrag hochgeladen! Die Analyse wird gestartet.');
      // Redirect to contract detail page
      router.push(`/vertraege/${response.id}`);
    } catch {
      addToast('error', 'Upload fehlgeschlagen. Bitte versuchen Sie es erneut.');
    }
  };

  // Show loading while checking auth
  if (authLoading) {
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
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center space-x-4">
          <Link href="/vertraege">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Zurück
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Vertrag analysieren
            </h1>
            <p className="text-gray-500 mt-1">
              Laden Sie einen Vertrag zur KI-Analyse hoch
            </p>
          </div>
        </div>

        {/* Upload form */}
        <Card>
          <CardHeader>
            <CardTitle>Dokument hochladen</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* File upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Vertragsdokument
              </label>
              <FileUpload
                onFileSelect={setFile}
                disabled={loading}
              />
            </div>

            {/* Contract type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Vertragstyp (optional)
              </label>
              <select
                value={contractType}
                onChange={(e) => setContractType(e.target.value)}
                disabled={loading}
                className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:opacity-50"
              >
                <option value="">Automatisch erkennen</option>
                {contractTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-sm text-gray-500">
                Die KI erkennt den Vertragstyp automatisch, aber Sie können
                diesen auch manuell angeben.
              </p>
            </div>

            {/* Error message */}
            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-3">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            {/* Submit */}
            <div className="flex justify-end space-x-3">
              <Link href="/vertraege">
                <Button variant="secondary" disabled={loading}>
                  Abbrechen
                </Button>
              </Link>
              <Button
                onClick={handleUpload}
                disabled={!file || loading}
                loading={loading}
              >
                {loading ? 'Wird hochgeladen...' : 'Analyse starten'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Info */}
        <Card>
          <CardContent className="py-4">
            <h3 className="font-medium text-gray-900 mb-2">Was wird analysiert?</h3>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="flex items-start">
                <span className="text-primary-600 mr-2">•</span>
                Haftungsklauseln und Gewährleistung
              </li>
              <li className="flex items-start">
                <span className="text-primary-600 mr-2">•</span>
                Zahlungsbedingungen und Fristen
              </li>
              <li className="flex items-start">
                <span className="text-primary-600 mr-2">•</span>
                Kündigungsklauseln und Auto-Renewal
              </li>
              <li className="flex items-start">
                <span className="text-primary-600 mr-2">•</span>
                Gerichtsstand und anwendbares Recht
              </li>
              <li className="flex items-start">
                <span className="text-primary-600 mr-2">•</span>
                Datenschutz und DSGVO-Konformität
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </Shell>
  );
}
