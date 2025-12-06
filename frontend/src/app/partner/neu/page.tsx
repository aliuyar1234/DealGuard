'use client';

import { Shell } from '@/components/layout/Shell';
import { Button, Card, CardContent, CardHeader, Input, useToast } from '@/components/ui';
import { useAuth } from '@/hooks/useAuth';
import { usePartner } from '@/hooks/usePartners';
import { ArrowLeft, Building2, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

const PARTNER_TYPES = [
  { value: 'supplier', label: 'Lieferant' },
  { value: 'customer', label: 'Kunde' },
  { value: 'service_provider', label: 'Dienstleister' },
  { value: 'distributor', label: 'Distributor' },
  { value: 'partner', label: 'Partner' },
  { value: 'other', label: 'Sonstige' },
];

export default function NewPartnerPage() {
  const router = useRouter();
  const { token, loading: authLoading } = useAuth();
  const { create, loading, error } = usePartner();
  const { addToast } = useToast();

  const [formData, setFormData] = useState({
    name: '',
    partner_type: 'other',
    handelsregister_id: '',
    vat_id: '',
    street: '',
    city: '',
    postal_code: '',
    country: 'DE',
    website: '',
    email: '',
    phone: '',
    notes: '',
  });

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !token) {
      router.push('/login');
    }
  }, [authLoading, token, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !formData.name.trim()) return;

    const partner = await create(
      {
        name: formData.name,
        partner_type: formData.partner_type,
        handelsregister_id: formData.handelsregister_id || undefined,
        vat_id: formData.vat_id || undefined,
        street: formData.street || undefined,
        city: formData.city || undefined,
        postal_code: formData.postal_code || undefined,
        country: formData.country,
        website: formData.website || undefined,
        email: formData.email || undefined,
        phone: formData.phone || undefined,
        notes: formData.notes || undefined,
      },
      token
    );

    if (partner) {
      addToast('success', 'Partner erfolgreich angelegt');
      router.push(`/partner/${partner.id}`);
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
        {/* Back link */}
        <Link
          href="/partner"
          className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Zurück zur Übersicht
        </Link>

        {/* Header */}
        <div className="flex items-center space-x-4">
          <div className="p-3 bg-primary-100 rounded-lg">
            <Building2 className="w-8 h-8 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Neuer Partner</h1>
            <p className="text-gray-500">Geschäftspartner anlegen</p>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold">Stammdaten</h2>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Name */}
              <Input
                label="Firmenname *"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Muster GmbH"
                required
              />

              {/* Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Partnertyp
                </label>
                <select
                  value={formData.partner_type}
                  onChange={(e) => setFormData({ ...formData, partner_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {PARTNER_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* IDs */}
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="Handelsregister"
                  value={formData.handelsregister_id}
                  onChange={(e) => setFormData({ ...formData, handelsregister_id: e.target.value })}
                  placeholder="HRB 12345"
                />
                <Input
                  label="USt-IdNr."
                  value={formData.vat_id}
                  onChange={(e) => setFormData({ ...formData, vat_id: e.target.value })}
                  placeholder="DE123456789"
                />
              </div>
            </CardContent>
          </Card>

          <Card className="mt-4">
            <CardHeader>
              <h2 className="text-lg font-semibold">Adresse</h2>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                label="Straße"
                value={formData.street}
                onChange={(e) => setFormData({ ...formData, street: e.target.value })}
                placeholder="Musterstraße 123"
              />
              <div className="grid grid-cols-3 gap-4">
                <Input
                  label="PLZ"
                  value={formData.postal_code}
                  onChange={(e) => setFormData({ ...formData, postal_code: e.target.value })}
                  placeholder="10115"
                />
                <div className="col-span-2">
                  <Input
                    label="Stadt"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    placeholder="Berlin"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Land
                </label>
                <select
                  value={formData.country}
                  onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="DE">Deutschland</option>
                  <option value="AT">Österreich</option>
                  <option value="CH">Schweiz</option>
                </select>
              </div>
            </CardContent>
          </Card>

          <Card className="mt-4">
            <CardHeader>
              <h2 className="text-lg font-semibold">Kontakt</h2>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                label="Website"
                value={formData.website}
                onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                placeholder="https://www.example.com"
                type="url"
              />
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="E-Mail"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="info@example.com"
                  type="email"
                />
                <Input
                  label="Telefon"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="+49 30 12345678"
                  type="tel"
                />
              </div>
            </CardContent>
          </Card>

          <Card className="mt-4">
            <CardHeader>
              <h2 className="text-lg font-semibold">Notizen</h2>
            </CardHeader>
            <CardContent>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Interne Notizen zum Partner..."
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </CardContent>
          </Card>

          {/* Error */}
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg mt-4">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end space-x-3 mt-6">
            <Link href="/partner">
              <Button variant="secondary" type="button">
                Abbrechen
              </Button>
            </Link>
            <Button type="submit" disabled={loading || !formData.name.trim()}>
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : null}
              Partner anlegen
            </Button>
          </div>
        </form>
      </div>
    </Shell>
  );
}
