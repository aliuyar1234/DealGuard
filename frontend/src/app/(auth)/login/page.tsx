'use client';

import { Button, Card, CardContent, CardHeader, CardTitle, Input, useToast } from '@/components/ui';
import { signIn } from '@/lib/auth/supabase';
import { Shield } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function LoginPage() {
  const router = useRouter();
  const { addToast } = useToast();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const { data, error } = await signIn(email, password);

      if (error) {
        if (error.message.includes('Invalid login')) {
          setError('E-Mail oder Passwort ist falsch');
        } else {
          setError(error.message);
        }
        return;
      }

      if (data.session) {
        addToast('success', 'Erfolgreich angemeldet!');
        router.push('/');
        router.refresh();
      }
    } catch {
      setError('Ein unerwarteter Fehler ist aufgetreten');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center justify-center mb-8">
          <Shield className="w-10 h-10 text-primary-600 mr-2" />
          <span className="text-2xl font-bold text-gray-900">DealGuard</span>
        </div>

        {/* Login Card */}
        <Card>
          <CardHeader className="text-center">
            <CardTitle>Anmelden</CardTitle>
            <p className="text-sm text-gray-500 mt-1">
              Melden Sie sich mit Ihrem Konto an
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email */}
              <div>
                <label htmlFor="email" className="label">
                  E-Mail
                </label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
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
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  autoComplete="current-password"
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
                Anmelden
              </Button>
            </form>

            {/* Links */}
            <div className="mt-6 text-center text-sm">
              <p className="text-gray-500">
                Noch kein Konto?{' '}
                <Link
                  href="/register"
                  className="text-primary-600 hover:text-primary-700 font-medium"
                >
                  Jetzt registrieren
                </Link>
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="mt-8 text-center text-xs text-gray-400">
          KI-gestützte Vertragsanalyse für KMU
        </p>
      </div>
    </div>
  );
}
