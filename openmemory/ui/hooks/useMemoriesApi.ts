import { useState, useCallback, useMemo } from 'react';
import axios from 'axios';
import { Memory, Client, Category } from '@/components/types';
import { useDispatch, useSelector } from 'react-redux';
import { AppDispatch, RootState } from '@/store/store';
import { setAccessLogs, setMemoriesSuccess, setSelectedMemory, setRelatedMemories } from '@/store/memoriesSlice';
import { UnifiedAPIClient } from '@/lib/api-adapter';
import { createUnifiedAPIConfig } from '@/lib/api-adapter/config';
import type { UnifiedMemory, UnifiedSearchOptions, UnifiedMemoryOptions } from '@/lib/types/unified';

// Define the new simplified memory type
export interface SimpleMemory {
  id: string;
  text: string;
  created_at: string;
  state: string;
  categories: string[];
  app_name: string;
}

// Define the shape of the API response item
interface ApiMemoryItem {
  id: string;
  content: string;
  created_at: string;
  state: string;
  app_id: string;
  categories: string[];
  metadata_?: Record<string, any>;
  app_name: string;
}

// Define the shape of the API response
interface ApiResponse {
  items: ApiMemoryItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

interface AccessLogEntry {
  id: string;
  app_name: string;
  accessed_at: string;
}

interface AccessLogResponse {
  total: number;
  page: number;
  page_size: number;
  logs: AccessLogEntry[];
}

interface RelatedMemoryItem {
  id: string;
  content: string;
  created_at: number;
  state: string;
  app_id: string;
  app_name: string;
  categories: string[];
  metadata_: Record<string, any>;
}

interface RelatedMemoriesResponse {
  items: RelatedMemoryItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

interface UseMemoriesApiReturn {
  fetchMemories: (
    query?: string,
    page?: number,
    size?: number,
    filters?: {
      apps?: string[];
      categories?: string[];
      sortColumn?: string;
      sortDirection?: 'asc' | 'desc';
      showArchived?: boolean;
    }
  ) => Promise<{ memories: Memory[]; total: number; pages: number }>;
  fetchMemoryById: (memoryId: string) => Promise<void>;
  fetchAccessLogs: (memoryId: string, page?: number, pageSize?: number) => Promise<void>;
  fetchRelatedMemories: (memoryId: string) => Promise<void>;
  createMemory: (text: string) => Promise<void>;
  deleteMemories: (memoryIds: string[]) => Promise<void>;
  updateMemory: (memoryId: string, content: string) => Promise<void>;
  updateMemoryState: (memoryIds: string[], state: string) => Promise<void>;
  isLoading: boolean;
  error: string | null;
  hasUpdates: number;
  memories: Memory[];
  selectedMemory: SimpleMemory | null;
}

export const useMemoriesApi = (): UseMemoriesApiReturn => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [hasUpdates, setHasUpdates] = useState<number>(0);
  const dispatch = useDispatch<AppDispatch>();
  const user_id = useSelector((state: RootState) => state.profile.userId);
  const memories = useSelector((state: RootState) => state.memories.memories);
  const selectedMemory = useSelector((state: RootState) => state.memories.selectedMemory);

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

  const fetchMemories = useCallback(async (
    query?: string,
    page: number = 1,
    size: number = 10,
    filters?: {
      apps?: string[];
      categories?: string[];
      sortColumn?: string;
      sortDirection?: 'asc' | 'desc';
      showArchived?: boolean;
    }
  ): Promise<{ memories: Memory[], total: number, pages: number }> => {
    setIsLoading(true);
    setError(null);
    try {
      // Use unified API client
      const searchOptions: UnifiedSearchOptions = {
        source: 'openmemory', // Maintain backward compatibility
        user_id: user_id,
        query: query,
        page: page,
        page_size: size,
        categories: filters?.categories,
      };

      const response = await unifiedClient.getMemories(searchOptions);

      // Transform unified memories back to legacy Memory format for compatibility
      const adaptedMemories: Memory[] = response.data.map((unifiedMemory) => ({
        id: unifiedMemory.id,
        memory: unifiedMemory.content,
        created_at: new Date(unifiedMemory.created_at).getTime(),
        state: unifiedMemory.state as "active" | "paused" | "archived" | "deleted",
        metadata: unifiedMemory.metadata || {},
        categories: unifiedMemory.categories as Category[],
        client: (unifiedMemory.client as Client) || 'api',
        app_name: unifiedMemory.app_name || 'unknown'
      }));

      setIsLoading(false);
      dispatch(setMemoriesSuccess(adaptedMemories));
      return {
        memories: adaptedMemories,
        total: adaptedMemories.length, // Unified response doesn't always have total
        pages: Math.ceil(adaptedMemories.length / size)
      };
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to fetch memories';
      setError(errorMessage);
      setIsLoading(false);
      throw new Error(errorMessage);
    }
  }, [user_id, dispatch, unifiedClient]);

  const createMemory = async (text: string): Promise<void> => {
    try {
      const options: UnifiedMemoryOptions = {
        source: 'openmemory', // Maintain backward compatibility
        user_id: user_id,
        app_name: "openmemory",
      };

      await unifiedClient.createMemory(text, options);
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to create memory';
      setError(errorMessage);
      setIsLoading(false);
      throw new Error(errorMessage);
    }
  };

  const deleteMemories = async (memory_ids: string[]) => {
    try {
      const options: UnifiedMemoryOptions = {
        source: 'openmemory', // Maintain backward compatibility
        user_id: user_id,
      };

      await unifiedClient.deleteMemories(memory_ids, options);
      dispatch(setMemoriesSuccess(memories.filter((memory: Memory) => !memory_ids.includes(memory.id))));
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to delete memories';
      setError(errorMessage);
      setIsLoading(false);
      throw new Error(errorMessage);
    }
  };

  const fetchMemoryById = async (memoryId: string): Promise<void> => {
    if (memoryId === "") {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const options: UnifiedMemoryOptions = {
        source: 'openmemory', // Maintain backward compatibility
        user_id: user_id,
      };

      const response = await unifiedClient.getMemoryById(memoryId, options);

      // Transform to SimpleMemory format for compatibility
      const simpleMemory: SimpleMemory = {
        id: response.data.id,
        text: response.data.content,
        created_at: response.data.created_at,
        state: response.data.state || 'active',
        categories: response.data.categories,
        app_name: response.data.app_name || 'unknown',
      };

      setIsLoading(false);
      dispatch(setSelectedMemory(simpleMemory));
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to fetch memory';
      setError(errorMessage);
      setIsLoading(false);
      throw new Error(errorMessage);
    }
  };

  const fetchAccessLogs = async (memoryId: string, page: number = 1, pageSize: number = 10): Promise<void> => {
    if (memoryId === "") {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await axios.get<AccessLogResponse>(
        `${URL}/api/v1/memories/${memoryId}/access-log?page=${page}&page_size=${pageSize}`
      );
      setIsLoading(false);
      dispatch(setAccessLogs(response.data.logs));
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to fetch access logs';
      setError(errorMessage);
      setIsLoading(false);
      throw new Error(errorMessage);
    }
  };

  const fetchRelatedMemories = async (memoryId: string): Promise<void> => {
    if (memoryId === "") {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await axios.get<RelatedMemoriesResponse>(
        `${URL}/api/v1/memories/${memoryId}/related?user_id=${user_id}`
      );

      const adaptedMemories: Memory[] = response.data.items.map((item: RelatedMemoryItem) => ({
        id: item.id,
        memory: item.content,
        created_at: item.created_at,
        state: item.state as "active" | "paused" | "archived" | "deleted",
        metadata: item.metadata_,
        categories: item.categories as Category[],
        client: 'api',
        app_name: item.app_name
      }));

      setIsLoading(false);
      dispatch(setRelatedMemories(adaptedMemories));
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to fetch related memories';
      setError(errorMessage);
      setIsLoading(false);
      throw new Error(errorMessage);
    }
  };

  const updateMemory = async (memoryId: string, content: string): Promise<void> => {
    if (memoryId === "") {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const options: UnifiedMemoryOptions = {
        source: 'openmemory', // Maintain backward compatibility
        user_id: user_id,
      };

      await unifiedClient.updateMemory(memoryId, content, options);
      setIsLoading(false);
      setHasUpdates(hasUpdates + 1);
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to update memory';
      setError(errorMessage);
      setIsLoading(false);
      throw new Error(errorMessage);
    }
  };

  const updateMemoryState = async (memoryIds: string[], state: string): Promise<void> => {
    if (memoryIds.length === 0) {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      await axios.post(`${URL}/api/v1/memories/actions/pause`, {
        memory_ids: memoryIds,
        all_for_app: true,
        state: state,
        user_id: user_id
      });
      dispatch(setMemoriesSuccess(memories.map((memory: Memory) => {
        if (memoryIds.includes(memory.id)) {
          return { ...memory, state: state as "active" | "paused" | "archived" | "deleted" };
        }
        return memory;
      })));

      // If archive, delete the memory
      if (state === "archived") {
        dispatch(setMemoriesSuccess(memories.filter((memory: Memory) => !memoryIds.includes(memory.id))));
      }

      // if selected memory, update it
      if (selectedMemory?.id && memoryIds.includes(selectedMemory.id)) {
        dispatch(setSelectedMemory({ ...selectedMemory, state: state as "active" | "paused" | "archived" | "deleted" }));
      }

      setIsLoading(false);
      setHasUpdates(hasUpdates + 1);
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to update memory state';
      setError(errorMessage);
      setIsLoading(false);
      throw new Error(errorMessage);
    }
  };

  return {
    fetchMemories,
    fetchMemoryById,
    fetchAccessLogs,
    fetchRelatedMemories,
    createMemory,
    deleteMemories,
    updateMemory,
    updateMemoryState,
    isLoading,
    error,
    hasUpdates,
    memories,
    selectedMemory
  };
};