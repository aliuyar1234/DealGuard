'use client';

import { useCallback, useState } from 'react';

/**
 * Generic async operation state and executor.
 * Reduces boilerplate for loading/error handling in hooks.
 *
 * @example
 * const { loading, error, execute } = useAsync<Contract>();
 *
 * const fetchContract = useCallback(async (id: string, token: string) => {
 *   return execute(() => getContract(id, token), 'Vertrag nicht gefunden');
 * }, [execute]);
 */
export interface UseAsyncReturn<T> {
  loading: boolean;
  error: string | null;
  execute: <R = T>(
    asyncFn: () => Promise<R>,
    defaultErrorMessage?: string
  ) => Promise<R>;
  executeWithThrow: <R = T>(
    asyncFn: () => Promise<R>,
    defaultErrorMessage?: string
  ) => Promise<R>;
  setError: (error: string | null) => void;
  clearError: () => void;
}

/**
 * Hook for managing async operations with loading and error states.
 *
 * Provides two execution methods:
 * - `execute`: Catches errors, sets error state, returns result or throws
 * - `executeWithThrow`: Catches errors, sets error state, always re-throws
 */
export function useAsync<T = unknown>(): UseAsyncReturn<T> {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Execute an async function, catching errors and managing state.
   * Returns the result on success, throws on error.
   */
  const execute = useCallback(
    async <R = T>(
      asyncFn: () => Promise<R>,
      defaultErrorMessage = 'Ein Fehler ist aufgetreten'
    ): Promise<R> => {
      setLoading(true);
      setError(null);
      try {
        const result = await asyncFn();
        return result;
      } catch (err) {
        const message = err instanceof Error ? err.message : defaultErrorMessage;
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  /**
   * Execute an async function, catching errors, managing state, and always re-throwing.
   * Use this when the caller needs to handle the error as well.
   */
  const executeWithThrow = useCallback(
    async <R = T>(
      asyncFn: () => Promise<R>,
      defaultErrorMessage = 'Ein Fehler ist aufgetreten'
    ): Promise<R> => {
      setLoading(true);
      setError(null);
      try {
        return await asyncFn();
      } catch (err) {
        const message = err instanceof Error ? err.message : defaultErrorMessage;
        setError(message);
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
    loading,
    error,
    execute,
    executeWithThrow,
    setError,
    clearError,
  };
}

/**
 * Hook for managing async operations that return null on error instead of throwing.
 * Useful for "fetch or null" patterns.
 */
export function useAsyncSafe<T = unknown>() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(
    async <R = T>(
      asyncFn: () => Promise<R>,
      defaultErrorMessage = 'Ein Fehler ist aufgetreten'
    ): Promise<R | null> => {
      setLoading(true);
      setError(null);
      try {
        return await asyncFn();
      } catch (err) {
        const message = err instanceof Error ? err.message : defaultErrorMessage;
        setError(message);
        return null;
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
    loading,
    error,
    execute,
    setError,
    clearError,
  };
}
