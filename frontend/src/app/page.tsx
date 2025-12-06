'use client';

import { Shell } from '@/components/layout/Shell';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { FileText, Plus, Shield, TrendingUp } from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  return (
    <Shell>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-gray-500 mt-1">
              Willkommen bei DealGuard - Ihrer KI-Vertragsanalyse
            </p>
          </div>
          <Link href="/vertraege/neu">
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Vertrag analysieren
            </Button>
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center space-x-4">
                <div className="p-3 bg-primary-100 rounded-lg">
                  <FileText className="w-6 h-6 text-primary-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">0</p>
                  <p className="text-sm text-gray-500">Analysierte Verträge</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center space-x-4">
                <div className="p-3 bg-green-100 rounded-lg">
                  <Shield className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">0</p>
                  <p className="text-sm text-gray-500">Erkannte Risiken</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center space-x-4">
                <div className="p-3 bg-yellow-100 rounded-lg">
                  <TrendingUp className="w-6 h-6 text-yellow-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">0</p>
                  <p className="text-sm text-gray-500">Diesen Monat</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick start */}
        <Card>
          <CardHeader>
            <CardTitle>Erste Schritte</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center py-8 text-center">
              <div className="p-4 bg-gray-100 rounded-full mb-4">
                <FileText className="w-12 h-12 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Noch keine Verträge analysiert
              </h3>
              <p className="text-gray-500 mb-6 max-w-md">
                Laden Sie Ihren ersten Vertrag hoch und erhalten Sie in weniger
                als 2 Minuten eine detaillierte Risikoanalyse.
              </p>
              <Link href="/vertraege/neu">
                <Button size="lg">
                  <Plus className="w-5 h-5 mr-2" />
                  Ersten Vertrag analysieren
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardContent className="pt-6">
              <h3 className="font-semibold text-gray-900 mb-2">
                Vertragsanalyse
              </h3>
              <p className="text-sm text-gray-500">
                Laden Sie PDF oder DOCX hoch. Unsere KI identifiziert
                Risiken in Haftung, Zahlungsbedingungen, Kündigungsklauseln
                und mehr.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <h3 className="font-semibold text-gray-900 mb-2">
                DACH Recht
              </h3>
              <p className="text-sm text-gray-500">
                Analyse nach BGB, ABGB und OR. Vergleich mit marktüblichen
                Standards und konkrete Handlungsempfehlungen.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </Shell>
  );
}
