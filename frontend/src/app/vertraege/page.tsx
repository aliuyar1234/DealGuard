'use client';

import { Shell } from '@/components/layout/Shell';
import { Badge, Button, Card, CardContent } from '@/components/ui';
import { useAuth } from '@/hooks/useAuth';
import { useContracts } from '@/hooks/useContracts';
import {
  formatDate,
  formatFileSize,
  getContractTypeLabel,
  getRiskLabel,
  getStatusLabel,
} from '@/lib/utils';
import { AlertCircle, FileText, Loader2, Plus, Search } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function ContractsPage() {
  const router = useRouter();
  const { token, loading: authLoading } = useAuth();
  const { contracts, loading, error, fetchContracts } = useContracts();
  const [searchQuery, setSearchQuery] = useState('');

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !token) {
      router.push('/login');
    }
  }, [authLoading, token, router]);

  // Fetch contracts when token is available
  useEffect(() => {
    if (token) {
      fetchContracts(token);
    }
  }, [token, fetchContracts]);

  // Filter contracts by search query
  const filteredContracts = contracts.filter((c) =>
    c.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getRiskBadgeVariant = (level: string) => {
    switch (level) {
      case 'low':
        return 'success';
      case 'medium':
        return 'warning';
      case 'high':
      case 'critical':
        return 'danger';
      default:
        return 'default';
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'info';
      case 'failed':
        return 'danger';
      default:
        return 'default';
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
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Verträge</h1>
            <p className="text-gray-500 mt-1">
              Alle analysierten Verträge im Überblick
            </p>
          </div>
          <Link href="/vertraege/neu">
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Neuer Vertrag
            </Button>
          </Link>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Verträge suchen..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        {/* Error */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
          </div>
        )}

        {/* Contract list */}
        {!loading && (
          <div className="space-y-4">
            {filteredContracts.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    {searchQuery ? 'Keine Treffer' : 'Keine Verträge vorhanden'}
                  </h3>
                  <p className="text-gray-500 mb-4">
                    {searchQuery
                      ? 'Versuchen Sie einen anderen Suchbegriff.'
                      : 'Laden Sie Ihren ersten Vertrag zur Analyse hoch.'}
                  </p>
                  {!searchQuery && (
                    <Link href="/vertraege/neu">
                      <Button>
                        <Plus className="w-4 h-4 mr-2" />
                        Vertrag hochladen
                      </Button>
                    </Link>
                  )}
                </CardContent>
              </Card>
            ) : (
              filteredContracts.map((contract) => (
                <Link key={contract.id} href={`/vertraege/${contract.id}`}>
                  <Card className="hover:border-primary-300 transition-colors cursor-pointer">
                    <CardContent className="py-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className="p-2 bg-gray-100 rounded-lg">
                            <FileText className="w-8 h-8 text-gray-600" />
                          </div>
                          <div>
                            <h3 className="font-medium text-gray-900">
                              {contract.filename}
                            </h3>
                            <div className="flex items-center space-x-3 mt-1 text-sm text-gray-500">
                              <span>{formatFileSize(contract.file_size_bytes)}</span>
                              <span>•</span>
                              <span>{contract.page_count || '?'} Seiten</span>
                              {contract.contract_type && (
                                <>
                                  <span>•</span>
                                  <span>
                                    {getContractTypeLabel(contract.contract_type)}
                                  </span>
                                </>
                              )}
                              <span>•</span>
                              <span>{formatDate(contract.created_at)}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-3">
                          {contract.analysis ? (
                            <div className="text-right">
                              <div className="text-2xl font-bold text-gray-900">
                                {contract.analysis.risk_score}
                              </div>
                              <Badge
                                variant={getRiskBadgeVariant(
                                  contract.analysis.risk_level
                                ) as any}
                              >
                                {getRiskLabel(contract.analysis.risk_level)}
                              </Badge>
                            </div>
                          ) : (
                            <Badge variant={getStatusBadgeVariant(contract.status) as any}>
                              {getStatusLabel(contract.status)}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))
            )}
          </div>
        )}
      </div>
    </Shell>
  );
}
