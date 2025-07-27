// useUnifiedApi Hook Unit Tests
import { renderHook, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { useUnifiedApi, useApiSourceSwitcher, useFeatureFlags } from '@/hooks/useUnifiedApi';
import { server } from '@/src/mocks/server';
import { openMemoryHandlers } from '@/src/mocks/handlers/openmemory';
import { mem0Handlers } from '@/src/mocks/handlers/mem0';

// Mock Redux store
const mockStore = configureStore({
  reducer: {
    profile: (state = { userId: 'test-user-123' }) => state,
  },
});

// Wrapper component for Redux Provider
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider store={mockStore}>{children}</Provider>
);

describe('useUnifiedApi Hook', () => {
  beforeAll(() => {
    server.listen({ onUnhandledRequest: 'error' });
  });

  beforeEach(() => {
    server.resetHandlers(...openMemoryHandlers, ...mem0Handlers);
  });

  afterEach(() => {
    server.resetHandlers();
  });

  afterAll(() => {
    server.close();
  });

  describe('Hook Initialization', () => {
    it('should initialize with default state', () => {
      const { result } = renderHook(() => useUnifiedApi(), { wrapper });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBe(null);
      expect(result.current.currentSource).toBeDefined();
      expect(typeof result.current.getMemories).toBe('function');
      expect(typeof result.current.createMemory).toBe('function');
      expect(typeof result.current.updateMemory).toBe('function');
      expect(typeof result.current.deleteMemories).toBe('function');
    });

    it('should provide feature flag management functions', () => {
      const { result } = renderHook(() => useUnifiedApi(), { wrapper });

      expect(typeof result.current.updateFeatureFlags).toBe('function');
      expect(typeof result.current.getFeatureFlags).toBe('function');
      expect(typeof result.current.isSourceAvailable).toBe('function');
    });
  });

  describe('Memory Operations', () => {
    it('should get memories successfully', async () => {
      const { result } = renderHook(() => useUnifiedApi(), { wrapper });

      await act(async () => {
        const response = await result.current.getMemories({
          source: 'openmemory',
          limit: 10,
        });

        expect(response).toHaveProperty('data');
        expect(response).toHaveProperty('status', 'success');
        expect(response).toHaveProperty('source');
        expect(Array.isArray(response.data)).toBe(true);
      });
    });

    it('should create memory successfully', async () => {
      const { result } = renderHook(() => useUnifiedApi(), { wrapper });

      await act(async () => {
        const response = await result.current.createMemory('Test memory content', {
          source: 'openmemory',
        });

        expect(response).toHaveProperty('data');
        expect(response).toHaveProperty('status', 'success');
        expect(Array.isArray(response.data)).toBe(true);
      });
    });

    it('should get memory by ID successfully', async () => {
      const { result } = renderHook(() => useUnifiedApi(), { wrapper });

      // First create a memory to get a valid ID
      let memoryId: string;
      await act(async () => {
        const createResponse = await result.current.createMemory('Test content', {
          source: 'openmemory',
        });
        memoryId = createResponse.data[0].id;
      });

      await act(async () => {
        const response = await result.current.getMemoryById(memoryId, {
          source: 'openmemory',
        });

        expect(response).toHaveProperty('data');
        expect(response).toHaveProperty('status', 'success');
        expect(response.data).toHaveProperty('id', memoryId);
      });
    });

    it('should update memory successfully', async () => {
      const { result } = renderHook(() => useUnifiedApi(), { wrapper });

      // First create a memory
      let memoryId: string;
      await act(async () => {
        const createResponse = await result.current.createMemory('Original content', {
          source: 'openmemory',
        });
        memoryId = createResponse.data[0].id;
      });

      await act(async () => {
        const response = await result.current.updateMemory(
          memoryId,
          'Updated content',
          { source: 'openmemory' }
        );

        expect(response).toHaveProperty('data');
        expect(response).toHaveProperty('status', 'success');
      });
    });

    it('should delete memories successfully', async () => {
      const { result } = renderHook(() => useUnifiedApi(), { wrapper });

      // First create a memory
      let memoryId: string;
      await act(async () => {
        const createResponse = await result.current.createMemory('To be deleted', {
          source: 'openmemory',
        });
        memoryId = createResponse.data[0].id;
      });

      await act(async () => {
        const response = await result.current.deleteMemories([memoryId], {
          source: 'openmemory',
        });

        expect(response).toHaveProperty('status', 'success');
      });
    });

    it('should search memories successfully', async () => {
      const { result } = renderHook(() => useUnifiedApi(), { wrapper });

      await act(async () => {
        const response = await result.current.searchMemories('test query', {
          source: 'openmemory',
          limit: 5,
        });

        expect(response).toHaveProperty('data');
        expect(response).toHaveProperty('status', 'success');
        expect(Array.isArray(response.data)).toBe(true);
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      const { result } = renderHook(() => useUnifiedApi(), { wrapper });

      await act(async () => {
        try {
          await result.current.getMemoryById('invalid-id', {
            source: 'openmemory',
          });
        } catch (error) {
          expect(error).toBeInstanceOf(Error);
        }
      });

      expect(result.current.error).toBeTruthy();
    });

    it('should set loading state during API calls', async () => {
      const { result } = renderHook(() => useUnifiedApi(), { wrapper });

      act(() => {
        result.current.getMemories({ source: 'openmemory' });
      });

      // Loading state should be true during the call
      expect(result.current.isLoading).toBe(true);
    });
  });

  describe('Feature Flag Management', () => {
    it('should get current feature flags', () => {
      const { result } = renderHook(() => useUnifiedApi(), { wrapper });

      const flags = result.current.getFeatureFlags();
      expect(flags).toHaveProperty('enableMem0');
      expect(flags).toHaveProperty('enableOpenMemory');
      expect(flags).toHaveProperty('defaultSource');
      expect(flags).toHaveProperty('enableAutoFallback');
    });

    it('should update feature flags', () => {
      const { result } = renderHook(() => useUnifiedApi(), { wrapper });

      act(() => {
        result.current.updateFeatureFlags({
          defaultSource: 'mem0',
          enableAutoFallback: false,
        });
      });

      const updatedFlags = result.current.getFeatureFlags();
      expect(updatedFlags.defaultSource).toBe('mem0');
      expect(updatedFlags.enableAutoFallback).toBe(false);
    });

    it('should check source availability', () => {
      const { result } = renderHook(() => useUnifiedApi(), { wrapper });

      const openMemoryAvailable = result.current.isSourceAvailable('openmemory');
      const mem0Available = result.current.isSourceAvailable('mem0');

      expect(typeof openMemoryAvailable).toBe('boolean');
      expect(typeof mem0Available).toBe('boolean');
    });
  });
});

describe('useApiSourceSwitcher Hook', () => {
  it('should provide source switching functions', () => {
    const { result } = renderHook(() => useApiSourceSwitcher(), { wrapper });

    expect(typeof result.current.switchToMem0).toBe('function');
    expect(typeof result.current.switchToOpenMemory).toBe('function');
    expect(typeof result.current.enableAutoFallback).toBe('function');
    expect(typeof result.current.getCurrentSource).toBe('function');
    expect(typeof result.current.isSourceAvailable).toBe('function');
  });

  it('should switch to OpenMemory', () => {
    const { result } = renderHook(() => useApiSourceSwitcher(), { wrapper });

    act(() => {
      result.current.switchToOpenMemory();
    });

    expect(result.current.getCurrentSource()).toBe('openmemory');
  });

  it('should enable/disable auto fallback', () => {
    const { result } = renderHook(() => useApiSourceSwitcher(), { wrapper });

    act(() => {
      result.current.enableAutoFallback(true);
    });

    // Should not throw
    expect(() => result.current.enableAutoFallback(false)).not.toThrow();
  });
});

describe('useFeatureFlags Hook', () => {
  it('should provide feature flag state and updaters', () => {
    const { result } = renderHook(() => useFeatureFlags(), { wrapper });

    expect(result.current.flags).toBeDefined();
    expect(typeof result.current.updateFlags).toBe('function');
    expect(typeof result.current.enableMem0).toBe('function');
    expect(typeof result.current.enableOpenMemory).toBe('function');
    expect(typeof result.current.setDefaultSource).toBe('function');
    expect(typeof result.current.enableAutoFallback).toBe('function');
  });

  it('should update individual flags', () => {
    const { result } = renderHook(() => useFeatureFlags(), { wrapper });

    act(() => {
      result.current.enableMem0(true);
    });

    expect(result.current.flags.enableMem0).toBe(true);

    act(() => {
      result.current.setDefaultSource('mem0');
    });

    expect(result.current.flags.defaultSource).toBe('mem0');
  });

  it('should update multiple flags at once', () => {
    const { result } = renderHook(() => useFeatureFlags(), { wrapper });

    act(() => {
      result.current.updateFlags({
        enableMem0: true,
        enableOpenMemory: false,
        defaultSource: 'mem0',
      });
    });

    expect(result.current.flags.enableMem0).toBe(true);
    expect(result.current.flags.enableOpenMemory).toBe(false);
    expect(result.current.flags.defaultSource).toBe('mem0');
  });
});
