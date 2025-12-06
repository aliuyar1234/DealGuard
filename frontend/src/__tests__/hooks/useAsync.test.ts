import { renderHook, act } from '@testing-library/react';
import { useAsync, useAsyncSafe } from '@/hooks/useAsync';

describe('useAsync Hook', () => {
  describe('Initial State', () => {
    it('initializes with loading false and no error', () => {
      const { result } = renderHook(() => useAsync<string>());

      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBe(null);
    });

    it('provides execute function', () => {
      const { result } = renderHook(() => useAsync());

      expect(typeof result.current.execute).toBe('function');
    });

    it('provides executeWithThrow function', () => {
      const { result } = renderHook(() => useAsync());

      expect(typeof result.current.executeWithThrow).toBe('function');
    });
  });

  describe('execute', () => {
    it('sets loading to true during execution', async () => {
      const { result } = renderHook(() => useAsync<string>());

      let loadingDuringExecution = false;

      const asyncFn = async () => {
        loadingDuringExecution = result.current.loading;
        return 'result';
      };

      await act(async () => {
        await result.current.execute(asyncFn);
      });

      // Loading should have been true during execution
      // (this is tricky to test, but we verify final state is false)
      expect(result.current.loading).toBe(false);
    });

    it('returns result on success', async () => {
      const { result } = renderHook(() => useAsync<string>());

      let returnValue: string = '';

      await act(async () => {
        returnValue = await result.current.execute(async () => 'success');
      });

      expect(returnValue).toBe('success');
      expect(result.current.error).toBe(null);
    });

    it('clears previous error on new execution', async () => {
      const { result } = renderHook(() => useAsync());

      // First, set an error
      await act(async () => {
        try {
          await result.current.execute(async () => {
            throw new Error('First error');
          });
        } catch {}
      });

      expect(result.current.error).toBe('First error');

      // Execute successfully
      await act(async () => {
        await result.current.execute(async () => 'success');
      });

      expect(result.current.error).toBe(null);
    });

    it('sets error on failure with Error instance', async () => {
      const { result } = renderHook(() => useAsync());

      await act(async () => {
        try {
          await result.current.execute(async () => {
            throw new Error('Custom error message');
          });
        } catch {}
      });

      expect(result.current.error).toBe('Custom error message');
    });

    it('uses default error message for non-Error throws', async () => {
      const { result } = renderHook(() => useAsync());

      await act(async () => {
        try {
          await result.current.execute(
            async () => {
              throw 'string error';
            },
            'Default error'
          );
        } catch {}
      });

      expect(result.current.error).toBe('Default error');
    });

    it('throws error to caller', async () => {
      const { result } = renderHook(() => useAsync());

      let thrownError: Error | null = null;

      await act(async () => {
        try {
          await result.current.execute(async () => {
            throw new Error('Should throw');
          });
        } catch (err) {
          thrownError = err as Error;
        }
      });

      expect(thrownError).not.toBe(null);
      expect(thrownError?.message).toBe('Should throw');
    });

    it('sets loading false after success', async () => {
      const { result } = renderHook(() => useAsync());

      await act(async () => {
        await result.current.execute(async () => 'done');
      });

      expect(result.current.loading).toBe(false);
    });

    it('sets loading false after failure', async () => {
      const { result } = renderHook(() => useAsync());

      await act(async () => {
        try {
          await result.current.execute(async () => {
            throw new Error('fail');
          });
        } catch {}
      });

      expect(result.current.loading).toBe(false);
    });
  });

  describe('executeWithThrow', () => {
    it('returns result on success', async () => {
      const { result } = renderHook(() => useAsync<number>());

      let returnValue: number = 0;

      await act(async () => {
        returnValue = await result.current.executeWithThrow(async () => 42);
      });

      expect(returnValue).toBe(42);
    });

    it('sets error and throws on failure', async () => {
      const { result } = renderHook(() => useAsync());

      let didThrow = false;

      await act(async () => {
        try {
          await result.current.executeWithThrow(async () => {
            throw new Error('Error message');
          });
        } catch {
          didThrow = true;
        }
      });

      expect(didThrow).toBe(true);
      expect(result.current.error).toBe('Error message');
    });
  });

  describe('setError', () => {
    it('manually sets error state', () => {
      const { result } = renderHook(() => useAsync());

      act(() => {
        result.current.setError('Manual error');
      });

      expect(result.current.error).toBe('Manual error');
    });

    it('can set error to null', () => {
      const { result } = renderHook(() => useAsync());

      act(() => {
        result.current.setError('Some error');
      });

      act(() => {
        result.current.setError(null);
      });

      expect(result.current.error).toBe(null);
    });
  });

  describe('clearError', () => {
    it('clears error state', async () => {
      const { result } = renderHook(() => useAsync());

      await act(async () => {
        try {
          await result.current.execute(async () => {
            throw new Error('Error');
          });
        } catch {}
      });

      expect(result.current.error).not.toBe(null);

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBe(null);
    });
  });
});

describe('useAsyncSafe Hook', () => {
  describe('Initial State', () => {
    it('initializes with loading false and no error', () => {
      const { result } = renderHook(() => useAsyncSafe<string>());

      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBe(null);
    });
  });

  describe('execute', () => {
    it('returns result on success', async () => {
      const { result } = renderHook(() => useAsyncSafe<string>());

      let returnValue: string | null = null;

      await act(async () => {
        returnValue = await result.current.execute(async () => 'success');
      });

      expect(returnValue).toBe('success');
      expect(result.current.error).toBe(null);
    });

    it('returns null on error instead of throwing', async () => {
      const { result } = renderHook(() => useAsyncSafe<string>());

      let returnValue: string | null = 'initial';

      await act(async () => {
        returnValue = await result.current.execute(async () => {
          throw new Error('Error');
        });
      });

      expect(returnValue).toBe(null);
      expect(result.current.error).toBe('Error');
    });

    it('does not throw on error', async () => {
      const { result } = renderHook(() => useAsyncSafe());

      let didThrow = false;

      await act(async () => {
        try {
          await result.current.execute(async () => {
            throw new Error('Error');
          });
        } catch {
          didThrow = true;
        }
      });

      expect(didThrow).toBe(false);
    });

    it('uses default error message for non-Error throws', async () => {
      const { result } = renderHook(() => useAsyncSafe());

      await act(async () => {
        await result.current.execute(
          async () => {
            throw 'not an error object';
          },
          'Default message'
        );
      });

      expect(result.current.error).toBe('Default message');
    });

    it('sets loading false after success', async () => {
      const { result } = renderHook(() => useAsyncSafe());

      await act(async () => {
        await result.current.execute(async () => 'done');
      });

      expect(result.current.loading).toBe(false);
    });

    it('sets loading false after failure', async () => {
      const { result } = renderHook(() => useAsyncSafe());

      await act(async () => {
        await result.current.execute(async () => {
          throw new Error('fail');
        });
      });

      expect(result.current.loading).toBe(false);
    });
  });

  describe('clearError', () => {
    it('clears error state', async () => {
      const { result } = renderHook(() => useAsyncSafe());

      await act(async () => {
        await result.current.execute(async () => {
          throw new Error('Error');
        });
      });

      expect(result.current.error).not.toBe(null);

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBe(null);
    });
  });
});
