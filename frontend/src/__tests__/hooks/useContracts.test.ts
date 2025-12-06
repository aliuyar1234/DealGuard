import { renderHook, act } from '@testing-library/react';
import { useContracts } from '@/hooks/useContracts';

// Mock the API client functions
const mockGetContracts = jest.fn();
const mockGetContract = jest.fn();
const mockUploadContract = jest.fn();
const mockTriggerAnalysis = jest.fn();
const mockDeleteContract = jest.fn();

jest.mock('@/lib/api/client', () => ({
  getContracts: (...args: unknown[]) => mockGetContracts(...args),
  getContract: (...args: unknown[]) => mockGetContract(...args),
  uploadContract: (...args: unknown[]) => mockUploadContract(...args),
  triggerAnalysis: (...args: unknown[]) => mockTriggerAnalysis(...args),
  deleteContract: (...args: unknown[]) => mockDeleteContract(...args),
}));

describe('useContracts Hook', () => {
  const mockToken = 'test-token';

  beforeEach(() => {
    jest.clearAllMocks();

    mockGetContracts.mockResolvedValue({
      items: [],
      total: 0,
    });

    mockGetContract.mockResolvedValue({
      id: 'contract-1',
      filename: 'test.pdf',
      status: 'completed',
    });

    mockUploadContract.mockResolvedValue({
      contract_id: 'new-contract-id',
      filename: 'uploaded.pdf',
    });

    mockTriggerAnalysis.mockResolvedValue({
      id: 'contract-1',
      status: 'analyzing',
    });

    mockDeleteContract.mockResolvedValue(undefined);
  });

  describe('Initial State', () => {
    it('initializes with empty contracts list', () => {
      const { result } = renderHook(() => useContracts());

      expect(result.current.contracts).toEqual([]);
      expect(result.current.total).toBe(0);
      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBe(null);
    });
  });

  describe('fetchContracts', () => {
    it('fetches contracts successfully', async () => {
      const mockContracts = [
        { id: 'c1', filename: 'contract1.pdf', status: 'completed' },
        { id: 'c2', filename: 'contract2.pdf', status: 'pending' },
      ];

      mockGetContracts.mockResolvedValue({
        items: mockContracts,
        total: 2,
      });

      const { result } = renderHook(() => useContracts());

      await act(async () => {
        await result.current.fetchContracts(mockToken);
      });

      expect(result.current.contracts).toEqual(mockContracts);
      expect(result.current.total).toBe(2);
      expect(result.current.loading).toBe(false);
    });

    it('passes limit and offset parameters', async () => {
      const { result } = renderHook(() => useContracts());

      await act(async () => {
        await result.current.fetchContracts(mockToken, 10, 20);
      });

      expect(mockGetContracts).toHaveBeenCalledWith(mockToken, 10, 20);
    });

    it('uses default limit and offset', async () => {
      const { result } = renderHook(() => useContracts());

      await act(async () => {
        await result.current.fetchContracts(mockToken);
      });

      expect(mockGetContracts).toHaveBeenCalledWith(mockToken, 20, 0);
    });

    it('sets error on fetch failure', async () => {
      mockGetContracts.mockRejectedValue(new Error('Network error'));

      const { result } = renderHook(() => useContracts());

      await act(async () => {
        await result.current.fetchContracts(mockToken);
      });

      expect(result.current.error).toBe('Network error');
      expect(result.current.loading).toBe(false);
    });

    it('uses fallback error message for non-Error exceptions', async () => {
      mockGetContracts.mockRejectedValue('string error');

      const { result } = renderHook(() => useContracts());

      await act(async () => {
        await result.current.fetchContracts(mockToken);
      });

      expect(result.current.error).toBe('Fehler beim Laden der Verträge');
    });
  });

  describe('fetchContract', () => {
    it('fetches single contract successfully', async () => {
      const mockContract = {
        id: 'c1',
        filename: 'contract.pdf',
        status: 'completed',
        analysis: { risk_score: 45 },
      };

      mockGetContract.mockResolvedValue(mockContract);

      const { result } = renderHook(() => useContracts());

      let contract;
      await act(async () => {
        contract = await result.current.fetchContract('c1', mockToken);
      });

      expect(contract).toEqual(mockContract);
      expect(mockGetContract).toHaveBeenCalledWith('c1', mockToken);
    });

    it('returns null on fetch failure', async () => {
      mockGetContract.mockRejectedValue(new Error('Not found'));

      const { result } = renderHook(() => useContracts());

      let contract;
      await act(async () => {
        contract = await result.current.fetchContract('invalid-id', mockToken);
      });

      expect(contract).toBe(null);
      expect(result.current.error).toBe('Not found');
    });
  });

  describe('upload', () => {
    it('uploads file successfully', async () => {
      const mockFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });
      const mockResponse = {
        contract_id: 'new-id',
        filename: 'test.pdf',
      };

      mockUploadContract.mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useContracts());

      let response;
      await act(async () => {
        response = await result.current.upload(mockFile, mockToken, 'employment');
      });

      expect(response).toEqual(mockResponse);
      expect(mockUploadContract).toHaveBeenCalledWith(mockFile, 'employment', mockToken);
    });

    it('sets error and throws on upload failure', async () => {
      const mockFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });
      mockUploadContract.mockRejectedValue(new Error('Upload failed'));

      const { result } = renderHook(() => useContracts());

      let thrownError;
      await act(async () => {
        try {
          await result.current.upload(mockFile, mockToken);
        } catch (err) {
          thrownError = err;
        }
      });

      expect(result.current.error).toBe('Upload failed');
      expect(thrownError).toBeDefined();
    });
  });

  describe('analyze', () => {
    it('triggers analysis successfully', async () => {
      const mockContract = {
        id: 'c1',
        status: 'analyzing',
      };

      mockTriggerAnalysis.mockResolvedValue(mockContract);

      const { result } = renderHook(() => useContracts());

      let contract;
      await act(async () => {
        contract = await result.current.analyze('c1', mockToken);
      });

      expect(contract).toEqual(mockContract);
      expect(mockTriggerAnalysis).toHaveBeenCalledWith('c1', mockToken);
    });

    it('sets error and throws on analysis failure', async () => {
      mockTriggerAnalysis.mockRejectedValue(new Error('Analysis error'));

      const { result } = renderHook(() => useContracts());

      let thrownError;
      await act(async () => {
        try {
          await result.current.analyze('c1', mockToken);
        } catch (err) {
          thrownError = err;
        }
      });

      expect(result.current.error).toBe('Analysis error');
      expect(thrownError).toBeDefined();
    });
  });

  describe('remove', () => {
    it('removes contract and updates state', async () => {
      const mockContracts = [
        { id: 'c1', filename: 'contract1.pdf' },
        { id: 'c2', filename: 'contract2.pdf' },
      ];

      mockGetContracts.mockResolvedValue({
        items: mockContracts,
        total: 2,
      });

      const { result } = renderHook(() => useContracts());

      // Load contracts first
      await act(async () => {
        await result.current.fetchContracts(mockToken);
      });

      expect(result.current.contracts.length).toBe(2);
      expect(result.current.total).toBe(2);

      // Remove one
      await act(async () => {
        await result.current.remove('c1', mockToken);
      });

      expect(result.current.contracts.length).toBe(1);
      expect(result.current.contracts[0].id).toBe('c2');
      expect(result.current.total).toBe(1);
    });

    it('sets error and throws on delete failure', async () => {
      mockDeleteContract.mockRejectedValue(new Error('Delete failed'));

      const { result } = renderHook(() => useContracts());

      let thrownError;
      await act(async () => {
        try {
          await result.current.remove('c1', mockToken);
        } catch (err) {
          thrownError = err;
        }
      });

      expect(result.current.error).toBe('Delete failed');
      expect(thrownError).toBeDefined();
    });
  });

  describe('clearError', () => {
    it('clears error state', async () => {
      mockGetContracts.mockRejectedValue(new Error('Error'));

      const { result } = renderHook(() => useContracts());

      await act(async () => {
        await result.current.fetchContracts(mockToken);
      });

      expect(result.current.error).not.toBe(null);

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBe(null);
    });
  });

  describe('Loading State', () => {
    it('sets loading during fetchContracts', async () => {
      let resolvePromise: (value: unknown) => void;
      mockGetContracts.mockReturnValue(
        new Promise((resolve) => {
          resolvePromise = resolve;
        })
      );

      const { result } = renderHook(() => useContracts());

      act(() => {
        result.current.fetchContracts(mockToken);
      });

      expect(result.current.loading).toBe(true);

      await act(async () => {
        resolvePromise!({ items: [], total: 0 });
      });

      expect(result.current.loading).toBe(false);
    });

    it('sets loading during upload', async () => {
      let resolvePromise: (value: unknown) => void;
      mockUploadContract.mockReturnValue(
        new Promise((resolve) => {
          resolvePromise = resolve;
        })
      );

      const { result } = renderHook(() => useContracts());
      const mockFile = new File([''], 'test.pdf');

      act(() => {
        result.current.upload(mockFile, mockToken);
      });

      expect(result.current.loading).toBe(true);

      await act(async () => {
        resolvePromise!({ contract_id: 'new-id' });
      });

      expect(result.current.loading).toBe(false);
    });
  });
});
