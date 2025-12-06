import { renderHook, act, waitFor } from '@testing-library/react';
import { usePartners, usePartner, usePartnerAlerts } from '@/hooks/usePartners';
import * as api from '@/lib/api/client';

// Mock the API client
jest.mock('@/lib/api/client', () => ({
  getPartners: jest.fn(),
  getPartner: jest.fn(),
  createPartner: jest.fn(),
  updatePartner: jest.fn(),
  deletePartner: jest.fn(),
  searchPartners: jest.fn(),
  runPartnerChecks: jest.fn(),
  getAlertCount: jest.fn(),
}));

describe('usePartners Hook', () => {
  const mockToken = 'test-token';
  const mockPartners = [
    {
      id: '1',
      name: 'Partner 1',
      partner_type: 'supplier',
      risk_score: 30,
      risk_level: 'low',
      created_at: '2024-01-01T00:00:00Z',
    },
    {
      id: '2',
      name: 'Partner 2',
      partner_type: 'customer',
      risk_score: 65,
      risk_level: 'medium',
      created_at: '2024-01-02T00:00:00Z',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('initializes with empty partners and loading false', () => {
    const { result } = renderHook(() => usePartners());

    expect(result.current.partners).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('fetches partners successfully', async () => {
    (api.getPartners as jest.Mock).mockResolvedValue({
      items: mockPartners,
      total: 2,
    });

    const { result } = renderHook(() => usePartners());

    await act(async () => {
      await result.current.fetchPartners(mockToken);
    });

    expect(result.current.partners).toEqual(mockPartners);
    expect(result.current.total).toBe(2);
    expect(result.current.loading).toBe(false);
  });

  it('handles fetch error', async () => {
    (api.getPartners as jest.Mock).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => usePartners());

    await act(async () => {
      await result.current.fetchPartners(mockToken);
    });

    expect(result.current.error).toBe('Network error');
    expect(result.current.loading).toBe(false);
  });

  it('searches partners successfully', async () => {
    const searchResults = [mockPartners[0]];
    (api.searchPartners as jest.Mock).mockResolvedValue(searchResults);

    const { result } = renderHook(() => usePartners());

    let searchResult;
    await act(async () => {
      searchResult = await result.current.search('Partner 1', mockToken);
    });

    expect(searchResult).toEqual(searchResults);
    expect(api.searchPartners).toHaveBeenCalledWith('Partner 1', mockToken, 20);
  });
});

describe('usePartner Hook', () => {
  const mockToken = 'test-token';
  const mockPartner = {
    id: '1',
    name: 'Test Partner',
    partner_type: 'supplier',
    risk_score: 45,
    risk_level: 'medium',
    created_at: '2024-01-01T00:00:00Z',
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('initializes with null partner', () => {
    const { result } = renderHook(() => usePartner());

    expect(result.current.partner).toBe(null);
    expect(result.current.loading).toBe(false);
  });

  it('fetches single partner successfully', async () => {
    (api.getPartner as jest.Mock).mockResolvedValue(mockPartner);

    const { result } = renderHook(() => usePartner());

    await act(async () => {
      await result.current.fetchPartner('1', mockToken);
    });

    expect(result.current.partner).toEqual(mockPartner);
    expect(api.getPartner).toHaveBeenCalledWith('1', mockToken);
  });

  it('creates partner successfully', async () => {
    const newPartner = { ...mockPartner, id: 'new-id' };
    (api.createPartner as jest.Mock).mockResolvedValue(newPartner);

    const { result } = renderHook(() => usePartner());

    const createData = {
      name: 'Test Partner',
      partner_type: 'supplier',
    };

    let created;
    await act(async () => {
      created = await result.current.create(createData, mockToken);
    });

    expect(created).toEqual(newPartner);
    expect(result.current.partner).toEqual(newPartner);
  });

  it('updates partner successfully', async () => {
    const updatedPartner = { ...mockPartner, name: 'Updated Name' };
    (api.updatePartner as jest.Mock).mockResolvedValue(updatedPartner);

    const { result } = renderHook(() => usePartner());

    await act(async () => {
      await result.current.update('1', { name: 'Updated Name' }, mockToken);
    });

    expect(result.current.partner).toEqual(updatedPartner);
  });

  it('deletes partner successfully', async () => {
    (api.deletePartner as jest.Mock).mockResolvedValue(undefined);

    const { result } = renderHook(() => usePartner());

    let deleted;
    await act(async () => {
      deleted = await result.current.remove('1', mockToken);
    });

    expect(deleted).toBe(true);
    expect(result.current.partner).toBe(null);
  });

  it('runs checks successfully', async () => {
    const mockChecks = [
      { id: 'check-1', check_type: 'credit', status: 'completed', risk_contribution: 20 },
    ];
    (api.runPartnerChecks as jest.Mock).mockResolvedValue(mockChecks);
    (api.getPartner as jest.Mock).mockResolvedValue(mockPartner);

    const { result } = renderHook(() => usePartner());

    let checks;
    await act(async () => {
      checks = await result.current.runChecks('1', mockToken);
    });

    expect(checks).toEqual(mockChecks);
    expect(api.runPartnerChecks).toHaveBeenCalledWith('1', mockToken);
  });
});

describe('usePartnerAlerts Hook', () => {
  const mockToken = 'test-token';

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('initializes with zero alert count', () => {
    const { result } = renderHook(() => usePartnerAlerts());

    expect(result.current.alertCount).toBe(0);
    expect(result.current.loading).toBe(false);
  });

  it('fetches alert count successfully', async () => {
    (api.getAlertCount as jest.Mock).mockResolvedValue({ unread_count: 5 });

    const { result } = renderHook(() => usePartnerAlerts());

    await act(async () => {
      await result.current.fetchAlertCount(mockToken);
    });

    expect(result.current.alertCount).toBe(5);
  });

  it('handles fetch alert count error gracefully', async () => {
    (api.getAlertCount as jest.Mock).mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => usePartnerAlerts());

    let count;
    await act(async () => {
      count = await result.current.fetchAlertCount(mockToken);
    });

    expect(count).toBe(0); // Returns 0 on error
  });
});
