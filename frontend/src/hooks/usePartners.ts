'use client';

import { useCallback, useState } from 'react';
import {
  Partner,
  PartnerCheck,
  CreatePartnerRequest,
  UpdatePartnerRequest,
  getPartners,
  getPartner,
  createPartner,
  updatePartner,
  deletePartner,
  searchPartners,
  runPartnerChecks,
  getAlertCount,
} from '@/lib/api/client';

export function usePartners() {
  const [partners, setPartners] = useState<Partner[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPartners = useCallback(async (token: string, limit = 20, offset = 0) => {
    setLoading(true);
    setError(null);
    try {
      const response = await getPartners(token, limit, offset);
      setPartners(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden der Partner');
    } finally {
      setLoading(false);
    }
  }, []);

  const search = useCallback(async (query: string, token: string, limit = 20) => {
    setLoading(true);
    setError(null);
    try {
      const results = await searchPartners(query, token, limit);
      return results;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler bei der Suche');
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    partners,
    total,
    loading,
    error,
    fetchPartners,
    search,
  };
}

export function usePartner() {
  const [partner, setPartner] = useState<Partner | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checkLoading, setCheckLoading] = useState(false);

  const fetchPartner = useCallback(async (partnerId: string, token: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPartner(partnerId, token);
      setPartner(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden des Partners');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const create = useCallback(async (data: CreatePartnerRequest, token: string) => {
    setLoading(true);
    setError(null);
    try {
      const newPartner = await createPartner(data, token);
      setPartner(newPartner);
      return newPartner;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Erstellen des Partners');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const update = useCallback(async (partnerId: string, data: UpdatePartnerRequest, token: string) => {
    setLoading(true);
    setError(null);
    try {
      const updated = await updatePartner(partnerId, data, token);
      setPartner(updated);
      return updated;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Aktualisieren des Partners');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const remove = useCallback(async (partnerId: string, token: string) => {
    setLoading(true);
    setError(null);
    try {
      await deletePartner(partnerId, token);
      setPartner(null);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Löschen des Partners');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const runChecks = useCallback(async (partnerId: string, token: string): Promise<PartnerCheck[]> => {
    setCheckLoading(true);
    setError(null);
    try {
      const checks = await runPartnerChecks(partnerId, token);
      // Refresh partner data to get updated risk score
      await fetchPartner(partnerId, token);
      return checks;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Ausführen der Checks');
      return [];
    } finally {
      setCheckLoading(false);
    }
  }, [fetchPartner]);

  return {
    partner,
    loading,
    error,
    checkLoading,
    fetchPartner,
    create,
    update,
    remove,
    runChecks,
  };
}

export function usePartnerAlerts() {
  const [alertCount, setAlertCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const fetchAlertCount = useCallback(async (token: string) => {
    setLoading(true);
    try {
      const { unread_count } = await getAlertCount(token);
      setAlertCount(unread_count);
      return unread_count;
    } catch {
      return 0;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    alertCount,
    loading,
    fetchAlertCount,
  };
}
