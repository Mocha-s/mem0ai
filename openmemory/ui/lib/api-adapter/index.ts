// Unified API Adapter - Main implementation
import axios, { AxiosInstance } from 'axios';
import { Mem0APIClient } from '@/lib/mem0-client';
import type { 
  UnifiedMemory, 
  UnifiedMemoryOptions, 
  UnifiedSearchOptions,
  UnifiedApiResponse,
  UnifiedConfig 
} from '@/lib/types/unified';
import type { Message } from '@/lib/types/mem0';
import {
  transformOpenMemoryToUnified,
  transformMem0ToUnified,
  transformUnifiedToOpenMemoryOptions,
  transformUnifiedToOpenMemorySearchOptions,
  transformUnifiedToMem0Options,
  transformUnifiedToMem0SearchOptions,
  transformTextToMem0Message,
  transformOpenMemoryContentToMem0Messages,
  transformOpenMemoryResponse,
  transformMem0Response,
} from './transformers';

/**
 * Feature flags for controlling functionality
 */
export interface FeatureFlags {
  enableMem0: boolean;
  enableOpenMemory: boolean;
  defaultSource: 'openmemory' | 'mem0';
  enableAutoFallback: boolean;
  enableCaching: boolean;
  enableTelemetry: boolean;
}

/**
 * Unified API Client Configuration
 */
export interface UnifiedAPIClientConfig {
  openMemoryConfig: {
    baseUrl: string;
    apiKey?: string;
  };
  mem0Config?: {
    apiKey: string;
    baseUrl?: string;
    organizationId?: string | number;
    projectId?: string | number;
  };
  featureFlags: FeatureFlags;
  timeout?: number;
}

/**
 * Unified API Client
 * 
 * Provides a single interface for both OpenMemory and Mem0 APIs,
 * with automatic data transformation and feature flag support.
 */
export class UnifiedAPIClient {
  private openMemoryClient: AxiosInstance;
  private mem0Client?: Mem0APIClient;
  private config: UnifiedAPIClientConfig;
  private featureFlags: FeatureFlags;

  constructor(config: UnifiedAPIClientConfig) {
    this.config = config;
    this.featureFlags = config.featureFlags;

    // Initialize OpenMemory client
    this.openMemoryClient = axios.create({
      baseURL: config.openMemoryConfig.baseUrl,
      timeout: config.timeout || 60000,
      headers: {
        'Content-Type': 'application/json',
        ...(config.openMemoryConfig.apiKey && {
          'Authorization': `Bearer ${config.openMemoryConfig.apiKey}`
        }),
      },
    });

    // Initialize Mem0 client if enabled and configured
    if (this.featureFlags.enableMem0 && config.mem0Config) {
      this.mem0Client = new Mem0APIClient({
        apiKey: config.mem0Config.apiKey,
        baseUrl: config.mem0Config.baseUrl,
        organizationId: config.mem0Config.organizationId,
        projectId: config.mem0Config.projectId,
        timeout: config.timeout,
      });
    }
  }

  /**
   * Get memories with unified interface
   */
  async getMemories(options: UnifiedSearchOptions = {}): Promise<UnifiedApiResponse<UnifiedMemory[]>> {
    const source = options.source || this.featureFlags.defaultSource;

    try {
      if (source === 'mem0' && this.featureFlags.enableMem0 && this.mem0Client) {
        return await this.getMem0Memories(options);
      } else if (source === 'openmemory' && this.featureFlags.enableOpenMemory) {
        return await this.getOpenMemoryMemories(options);
      } else {
        // Fallback logic
        if (this.featureFlags.enableAutoFallback) {
          if (this.featureFlags.enableOpenMemory) {
            return await this.getOpenMemoryMemories(options);
          } else if (this.featureFlags.enableMem0 && this.mem0Client) {
            return await this.getMem0Memories(options);
          }
        }
        throw new Error(`No available API source for request. Source: ${source}`);
      }
    } catch (error: any) {
      // Auto-fallback on error if enabled
      if (this.featureFlags.enableAutoFallback && source !== 'openmemory' && this.featureFlags.enableOpenMemory) {
        console.warn(`Failed to fetch from ${source}, falling back to OpenMemory:`, error.message);
        return await this.getOpenMemoryMemories(options);
      }
      throw error;
    }
  }

  /**
   * Get memories from OpenMemory API
   */
  private async getOpenMemoryMemories(options: UnifiedSearchOptions): Promise<UnifiedApiResponse<UnifiedMemory[]>> {
    const searchOptions = transformUnifiedToOpenMemorySearchOptions(options);
    
    const response = await this.openMemoryClient.post('/api/v1/memories/filter', {
      user_id: options.user_id,
      page: options.page || 1,
      size: options.page_size || 10,
      search_query: options.query,
      app_ids: searchOptions.apps,
      category_ids: searchOptions.categories,
      sort_column: searchOptions.sortColumn?.toLowerCase(),
      sort_direction: searchOptions.sortDirection,
      show_archived: searchOptions.showArchived,
    });

    const transformedResponse = transformOpenMemoryResponse(response.data);
    
    return {
      data: transformedResponse.memories,
      status: 'success',
      source: 'openmemory',
    };
  }

  /**
   * Get memories from Mem0 API
   */
  private async getMem0Memories(options: UnifiedSearchOptions): Promise<UnifiedApiResponse<UnifiedMemory[]>> {
    if (!this.mem0Client) {
      throw new Error('Mem0 client not initialized');
    }

    const searchOptions = transformUnifiedToMem0SearchOptions(options);
    const memories = await this.mem0Client.getAll(searchOptions);
    const transformedResponse = transformMem0Response(memories);

    return {
      data: transformedResponse.memories,
      status: 'success',
      source: 'mem0',
    };
  }

  /**
   * Get a specific memory by ID
   */
  async getMemoryById(memoryId: string, options: UnifiedMemoryOptions = {}): Promise<UnifiedApiResponse<UnifiedMemory>> {
    const source = options.source || this.featureFlags.defaultSource;

    try {
      if (source === 'mem0' && this.featureFlags.enableMem0 && this.mem0Client) {
        const memory = await this.mem0Client.get(memoryId);
        return {
          data: transformMem0ToUnified(memory),
          status: 'success',
          source: 'mem0',
        };
      } else if (source === 'openmemory' && this.featureFlags.enableOpenMemory) {
        const response = await this.openMemoryClient.get(`/api/v1/memories/${memoryId}`, {
          params: { user_id: options.user_id },
        });
        return {
          data: transformOpenMemoryToUnified(response.data),
          status: 'success',
          source: 'openmemory',
        };
      } else {
        throw new Error(`No available API source for request. Source: ${source}`);
      }
    } catch (error: any) {
      if (this.featureFlags.enableAutoFallback && source !== 'openmemory' && this.featureFlags.enableOpenMemory) {
        console.warn(`Failed to fetch from ${source}, falling back to OpenMemory:`, error.message);
        const response = await this.openMemoryClient.get(`/api/v1/memories/${memoryId}`, {
          params: { user_id: options.user_id },
        });
        return {
          data: transformOpenMemoryToUnified(response.data),
          status: 'success',
          source: 'openmemory',
        };
      }
      throw error;
    }
  }

  /**
   * Create a new memory
   */
  async createMemory(content: string, options: UnifiedMemoryOptions = {}): Promise<UnifiedApiResponse<UnifiedMemory[]>> {
    const source = options.source || this.featureFlags.defaultSource;

    if (source === 'mem0' && this.featureFlags.enableMem0 && this.mem0Client) {
      const messages = transformOpenMemoryContentToMem0Messages(content);
      const mem0Options = transformUnifiedToMem0Options(options);
      const memories = await this.mem0Client.add(messages, mem0Options);
      const transformedResponse = transformMem0Response(memories);
      
      return {
        data: transformedResponse.memories,
        status: 'success',
        source: 'mem0',
      };
    } else if (source === 'openmemory' && this.featureFlags.enableOpenMemory) {
      const response = await this.openMemoryClient.post('/api/v1/memories/', {
        user_id: options.user_id,
        text: content,
        infer: false,
        app: options.app_name || "openmemory",
      });
      
      return {
        data: [transformOpenMemoryToUnified(response.data)],
        status: 'success',
        source: 'openmemory',
      };
    } else {
      throw new Error(`No available API source for request. Source: ${source}`);
    }
  }

  /**
   * Update a memory
   */
  async updateMemory(memoryId: string, content: string, options: UnifiedMemoryOptions = {}): Promise<UnifiedApiResponse<UnifiedMemory[]>> {
    const source = options.source || this.featureFlags.defaultSource;

    if (source === 'mem0' && this.featureFlags.enableMem0 && this.mem0Client) {
      const memories = await this.mem0Client.update(memoryId, content);
      const transformedResponse = transformMem0Response(memories);
      
      return {
        data: transformedResponse.memories,
        status: 'success',
        source: 'mem0',
      };
    } else if (source === 'openmemory' && this.featureFlags.enableOpenMemory) {
      await this.openMemoryClient.put(`/api/v1/memories/${memoryId}`, {
        memory_id: memoryId,
        memory_content: content,
        user_id: options.user_id,
      });
      
      // OpenMemory update doesn't return the updated memory, so we fetch it
      const updatedMemory = await this.getMemoryById(memoryId, options);
      
      return {
        data: [updatedMemory.data],
        status: 'success',
        source: 'openmemory',
      };
    } else {
      throw new Error(`No available API source for request. Source: ${source}`);
    }
  }

  /**
   * Delete memories
   */
  async deleteMemories(memoryIds: string[], options: UnifiedMemoryOptions = {}): Promise<UnifiedApiResponse<void>> {
    const source = options.source || this.featureFlags.defaultSource;

    if (source === 'mem0' && this.featureFlags.enableMem0 && this.mem0Client) {
      if (memoryIds.length === 1) {
        await this.mem0Client.delete(memoryIds[0]);
      } else {
        await this.mem0Client.batchDelete(memoryIds);
      }
      
      return {
        data: undefined,
        status: 'success',
        source: 'mem0',
      };
    } else if (source === 'openmemory' && this.featureFlags.enableOpenMemory) {
      await this.openMemoryClient.delete('/api/v1/memories/', {
        data: { 
          memory_ids: memoryIds, 
          user_id: options.user_id 
        },
      });
      
      return {
        data: undefined,
        status: 'success',
        source: 'openmemory',
      };
    } else {
      throw new Error(`No available API source for request. Source: ${source}`);
    }
  }

  /**
   * Search memories
   */
  async searchMemories(query: string, options: UnifiedSearchOptions = {}): Promise<UnifiedApiResponse<UnifiedMemory[]>> {
    return this.getMemories({ ...options, query });
  }

  /**
   * Update feature flags
   */
  updateFeatureFlags(flags: Partial<FeatureFlags>): void {
    this.featureFlags = { ...this.featureFlags, ...flags };
  }

  /**
   * Get current feature flags
   */
  getFeatureFlags(): FeatureFlags {
    return { ...this.featureFlags };
  }

  /**
   * Check if a source is available
   */
  isSourceAvailable(source: 'openmemory' | 'mem0'): boolean {
    if (source === 'openmemory') {
      return this.featureFlags.enableOpenMemory;
    } else if (source === 'mem0') {
      return this.featureFlags.enableMem0 && !!this.mem0Client;
    }
    return false;
  }
}

// Export types and utilities
export * from './transformers';
export type { UnifiedAPIClientConfig, FeatureFlags };
