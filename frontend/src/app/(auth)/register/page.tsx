'use client';

import { Button, Card, CardContent, CardHeader, CardTitle, Input, useToast } from '@/components/ui';
import { signUp } from '@/lib/auth/supabase';
import { Shield } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function RegisterPage() {
  const router = useRouter();
  const { addToast } = useToast();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    passwordConfirm: '',
    fullName: '',
    organizationName: '',
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (formData.password !== formData.passwordConfirm) {
      setError('Passwörter stimmen nicht überein');
      return;
    }

    if (formData.password.length < 8) {
      setError('Passwort muss mindestens 8 Zeichen lang sein');
      return;
    }

    setLoading(true);

    try {
      const { data, error } = await signUp(formData.email, formData.password, {
        full_name: formData.fullName,
        organization_name: formData.organizationName,
      });

      if (error) {
        if (error.message.includes('already registered')) {
          setError('Diese E-Mail-Adresse ist bereits registriert');
        } else {
          setError(error.message);
        }
        return;
      }

      // Show success message (Supabase may require email confirmation)
      addToast('success', 'Registrierung erfolgreich! Bitte bestätigen Sie Ihre E-Mail.');
      setSuccess(true);
    } catch (err) {
      setError('Ein unerwarteter Fehler ist aufgetreten');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
        <div className="w-full max-w-md">
          <Card>
            <CardContent className="py-8 text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Shield className="w-8 h-8 text-green-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Registrierung erfolgreich!
              </h2>
              <p className="text-gray-500 mb-6">
                Bitte überprüfen Sie Ihre E-Mail-Adresse, um Ihr Konto zu bestätigen.
              </p>
              <Link href="/login">
                <Button>Zur Anmeldung</Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center justify-center mb-8">
          <Shield className="w-10 h-10 text-primary-600 mr-2" />
          <span className="text-2xl font-bold text-gray-900">DealGuard</span>
        </div>

        {/* Register Card */}
        <Card>
          <CardHeader className="text-center">
            <CardTitle>Konto erstellen</CardTitle>
            <p className="text-sm text-gray-500 mt-1">
              Starten Sie mit der kostenlosen Testversion
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Full Name */}
              <div>
                <label htmlFor="fullName" className="label">
                  Ihr Name
                </label>
                <Input
                  id="fullName"
                  name="fullName"
                  type="text"
                  value={formData.fullName}
                  onChange={handleChange}
                  placeholder="Max Mustermann"
                  required
                  disabled={loading}
                />
              </div>

              {/* Organization */}
              <div>
                <label htmlFor="organizationName" className="label">
                  Firmenname
                </label>
                <Input
                  id="organizationName"
                  name="organizationName"
                  type="text"
                  value={formData.organizationName}
                  onChange={handleChange}
                  placeholder="Musterfirma GmbH"
                  required
                  disabled={loading}
                />
              </div>

              {/* Email */}
              <div>
                <label htmlFor="email" className="label">
                  E-Mail
                </label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="name@firma.de"
                  required
                  autoComplete="email"
                  disabled={loading}
                />
              </div>

              {/* Password */}
              <div>
                <label htmlFor="password" className="label">
                  Passwort
                </label>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Mindestens 8 Zeichen"
                  required
                  autoComplete="new-password"
                  disabled={loading}
                />
              </div>

              {/* Password Confirm */}
              <div>
                <label htmlFor="passwordConfirm" className="label">
                  Passwort bestätigen
                </label>
                <Input
                  id="passwordConfirm"
                  name="passwordConfirm"
                  type="password"
                  value={formData.passwordConfirm}
                  onChange={handleChange}
                  placeholder="Passwort wiederholen"
                  required
                  autoComplete="new-password"
                  disabled={loading}
                />
              </div>

              {/* Error */}
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              {/* Submit */}
              <Button
                type="submit"
                className="w-full"
                loading={loading}
                disabled={loading}
              >
                Kostenlos registrieren
              </Button>

              {/* Terms */}
              <p className="text-xs text-gray-500 text-center">
                Mit der Registrierung akzeptieren Sie unsere{' '}
                <a href="#" className="text-primary-600 hover:underline">
                  Nutzungsbedingungen
                </a>{' '}
                und{' '}
                <a href="#" className="text-primary-600 hover:underline">
                  Datenschutzerklärung
                </a>
                .
              </p>
            </form>

            {/* Links */}
            <div className="mt-6 text-center text-sm">
              <p className="text-gray-500">
                Bereits ein Konto?{' '}
                <Link
                  href="/login"
                  className="text-primary-600 hover:text-primary-700 font-medium"
                >
                  Jetzt anmelden
                </Link>
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
