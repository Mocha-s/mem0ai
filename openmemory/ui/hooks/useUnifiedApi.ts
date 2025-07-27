// Unified API Hook - Provides feature flag control and API switching
import { useState, useCallback, useMemo, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '@/store/store';
import { UnifiedAPIClient } from '@/lib/api-adapter';
import { createUnifiedAPIConfig, configManager } from '@/lib/api-adapter/config';
import type { 
  UnifiedMemory, 
  UnifiedMemoryOptions, 
  UnifiedSearchOptions,
  UnifiedApiResponse 
} from '@/lib/types/unified';
import type { FeatureFlags } from '@/lib/api-adapter';

export interface UseUnifiedApiReturn {
  // Core API methods
  getMemories: (options?: UnifiedSearchOptions) => Promise<UnifiedApiResponse<UnifiedMemory[]>>;
  getMemoryById: (memoryId: string, options?: UnifiedMemoryOptions) => Promise<UnifiedApiResponse<UnifiedMemory>>;
  createMemory: (content: string, options?: UnifiedMemoryOptions) => Promise<UnifiedApiResponse<UnifiedMemory[]>>;
  updateMemory: (memoryId: string, content: string, options?: UnifiedMemoryOptions) => Promise<UnifiedApiResponse<UnifiedMemory[]>>;
  deleteMemories: (memoryIds: string[], options?: UnifiedMemoryOptions) => Promise<UnifiedApiResponse<void>>;
  searchMemories: (query: string, options?: UnifiedSearchOptions) => Promise<UnifiedApiResponse<UnifiedMemory[]>>;
  
  // Feature flag management
  updateFeatureFlags: (flags: Partial<FeatureFlags>) => void;
  getFeatureFlags: () => FeatureFlags;
  isSourceAvailable: (source: 'openmemory' | 'mem0') => boolean;
  
  // State
  isLoading: boolean;
  error: string | null;
  currentSource: 'openmemory' | 'mem0';
}

export const useUnifiedApi = (): UseUnifiedApiReturn => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const user_id = useSelector((state: RootState) => state.profile.userId);
  
  const URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8765";

  // Initialize unified API client
  const unifiedClient = useMemo(() => {
    const config = createUnifiedAPIConfig({
      openMemoryConfig: {
        baseUrl: URL,
      },
    });
    return new UnifiedAPIClient(config);
  }, [URL]);

  // Get current feature flags
  const featureFlags = unifiedClient.getFeatureFlags();
  const currentSource = featureFlags.defaultSource;

  // Wrapper function for API calls with error handling
  const withErrorHandling = useCallback(async <T>(
    apiCall: () => Promise<T>
  ): Promise<T> => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiCall();
      setIsLoading(false);
      return result;
    } catch (err: any) {
      const errorMessage = err.message || 'API request failed';
      setError(errorMessage);
      setIsLoading(false);
      throw new Error(errorMessage);
    }
  }, []);

  // Core API methods
  const getMemories = useCallback(async (
    options: UnifiedSearchOptions = {}
  ): Promise<UnifiedApiResponse<UnifiedMemory[]>> => {
    return withErrorHandling(async () => {
      const searchOptions = {
        user_id,
        ...options,
      };
      return await unifiedClient.getMemories(searchOptions);
    });
  }, [unifiedClient, user_id, withErrorHandling]);

  const getMemoryById = useCallback(async (
    memoryId: string,
    options: UnifiedMemoryOptions = {}
  ): Promise<UnifiedApiResponse<UnifiedMemory>> => {
    return withErrorHandling(async () => {
      const memoryOptions = {
        user_id,
        ...options,
      };
      return await unifiedClient.getMemoryById(memoryId, memoryOptions);
    });
  }, [unifiedClient, user_id, withErrorHandling]);

  const createMemory = useCallback(async (
    content: string,
    options: UnifiedMemoryOptions = {}
  ): Promise<UnifiedApiResponse<UnifiedMemory[]>> => {
    return withErrorHandling(async () => {
      const memoryOptions = {
        user_id,
        ...options,
      };
      return await unifiedClient.createMemory(content, memoryOptions);
    });
  }, [unifiedClient, user_id, withErrorHandling]);

  const updateMemory = useCallback(async (
    memoryId: string,
    content: string,
    options: UnifiedMemoryOptions = {}
  ): Promise<UnifiedApiResponse<UnifiedMemory[]>> => {
    return withErrorHandling(async () => {
      const memoryOptions = {
        user_id,
        ...options,
      };
      return await unifiedClient.updateMemory(memoryId, content, memoryOptions);
    });
  }, [unifiedClient, user_id, withErrorHandling]);

  const deleteMemories = useCallback(async (
    memoryIds: string[],
    options: UnifiedMemoryOptions = {}
  ): Promise<UnifiedApiResponse<void>> => {
    return withErrorHandling(async () => {
      const memoryOptions = {
        user_id,
        ...options,
      };
      return await unifiedClient.deleteMemories(memoryIds, memoryOptions);
    });
  }, [unifiedClient, user_id, withErrorHandling]);

  const searchMemories = useCallback(async (
    query: string,
    options: UnifiedSearchOptions = {}
  ): Promise<UnifiedApiResponse<UnifiedMemory[]>> => {
    return withErrorHandling(async () => {
      const searchOptions = {
        user_id,
        query,
        ...options,
      };
      return await unifiedClient.searchMemories(query, searchOptions);
    });
  }, [unifiedClient, user_id, withErrorHandling]);

  // Feature flag management
  const updateFeatureFlags = useCallback((flags: Partial<FeatureFlags>) => {
    unifiedClient.updateFeatureFlags(flags);
    configManager.updateFeatureFlags(flags);
  }, [unifiedClient]);

  const getFeatureFlags = useCallback(() => {
    return unifiedClient.getFeatureFlags();
  }, [unifiedClient]);

  const isSourceAvailable = useCallback((source: 'openmemory' | 'mem0') => {
    return unifiedClient.isSourceAvailable(source);
  }, [unifiedClient]);

  return {
    // Core API methods
    getMemories,
    getMemoryById,
    createMemory,
    updateMemory,
    deleteMemories,
    searchMemories,
    
    // Feature flag management
    updateFeatureFlags,
    getFeatureFlags,
    isSourceAvailable,
    
    // State
    isLoading,
    error,
    currentSource,
  };
};

// Hook for switching between API sources
export const useApiSourceSwitcher = () => {
  const { updateFeatureFlags, getFeatureFlags, isSourceAvailable } = useUnifiedApi();
  
  const switchToMem0 = useCallback(() => {
    if (isSourceAvailable('mem0')) {
      updateFeatureFlags({
        defaultSource: 'mem0',
        enableMem0: true,
      });
    } else {
      throw new Error('Mem0 API is not available or not configured');
    }
  }, [updateFeatureFlags, isSourceAvailable]);

  const switchToOpenMemory = useCallback(() => {
    if (isSourceAvailable('openmemory')) {
      updateFeatureFlags({
        defaultSource: 'openmemory',
        enableOpenMemory: true,
      });
    } else {
      throw new Error('OpenMemory API is not available');
    }
  }, [updateFeatureFlags, isSourceAvailable]);

  const enableAutoFallback = useCallback((enabled: boolean) => {
    updateFeatureFlags({
      enableAutoFallback: enabled,
    });
  }, [updateFeatureFlags]);

  const getCurrentSource = useCallback(() => {
    return getFeatureFlags().defaultSource;
  }, [getFeatureFlags]);

  return {
    switchToMem0,
    switchToOpenMemory,
    enableAutoFallback,
    getCurrentSource,
    isSourceAvailable,
  };
};

// Hook for feature flag management
export const useFeatureFlags = () => {
  const { updateFeatureFlags, getFeatureFlags } = useUnifiedApi();
  const [flags, setFlags] = useState<FeatureFlags>(getFeatureFlags());

  useEffect(() => {
    const unsubscribe = configManager.subscribe((config) => {
      setFlags(config.featureFlags);
    });
    return unsubscribe;
  }, []);

  const updateFlags = useCallback((newFlags: Partial<FeatureFlags>) => {
    updateFeatureFlags(newFlags);
    setFlags(prev => ({ ...prev, ...newFlags }));
  }, [updateFeatureFlags]);

  return {
    flags,
    updateFlags,
    enableMem0: (enabled: boolean) => updateFlags({ enableMem0: enabled }),
    enableOpenMemory: (enabled: boolean) => updateFlags({ enableOpenMemory: enabled }),
    setDefaultSource: (source: 'openmemory' | 'mem0') => updateFlags({ defaultSource: source }),
    enableAutoFallback: (enabled: boolean) => updateFlags({ enableAutoFallback: enabled }),
  };
};
