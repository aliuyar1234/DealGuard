'use client';

import {
  Contract,
  ContractListResponse,
  deleteContract,
  getContract,
  getContracts,
  triggerAnalysis,
  uploadContract,
  UploadResponse,
} from '@/lib/api/client';
import { useCallback, useState } from 'react';

interface UseContractsReturn {
  contracts: Contract[];
  total: number;
  loading: boolean;
  error: string | null;
  fetchContracts: (token: string, limit?: number, offset?: number) => Promise<void>;
  fetchContract: (id: string, token: string) => Promise<Contract | null>;
  upload: (file: File, token: string, contractType?: string) => Promise<UploadResponse>;
  analyze: (id: string, token: string) => Promise<Contract>;
  remove: (id: string, token: string) => Promise<void>;
  clearError: () => void;
}

export function useContracts(): UseContractsReturn {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchContracts = useCallback(
    async (token: string, limit = 20, offset = 0) => {
      setLoading(true);
      setError(null);
      try {
        const response = await getContracts(token, limit, offset);
        setContracts(response.items);
        setTotal(response.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Fehler beim Laden der Verträge');
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const fetchContract = useCallback(
    async (id: string, token: string): Promise<Contract | null> => {
      setLoading(true);
      setError(null);
      try {
        return await getContract(id, token);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Vertrag nicht gefunden');
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const upload = useCallback(
    async (file: File, token: string, contractType?: string): Promise<UploadResponse> => {
      setLoading(true);
      setError(null);
      try {
        return await uploadContract(file, contractType, token);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Upload fehlgeschlagen';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const analyze = useCallback(
    async (id: string, token: string): Promise<Contract> => {
      setLoading(true);
      setError(null);
      try {
        return await triggerAnalysis(id, token);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Analyse fehlgeschlagen';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const remove = useCallback(
    async (id: string, token: string): Promise<void> => {
      setLoading(true);
      setError(null);
      try {
        await deleteContract(id, token);
        setContracts((prev) => prev.filter((c) => c.id !== id));
        setTotal((prev) => prev - 1);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Löschen fehlgeschlagen');
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    contracts,
    total,
    loading,
    error,
    fetchContracts,
    fetchContract,
    upload,
    analyze,
    remove,
    clearError,
  };
}
