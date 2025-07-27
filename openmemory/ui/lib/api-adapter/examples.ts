// API Adapter Usage Examples
import { UnifiedAPIClient } from './index';
import { createUnifiedAPIConfig, CONFIG_PRESETS } from './config';
import type { UnifiedMemoryOptions, UnifiedSearchOptions } from '@/lib/types/unified';

/**
 * Example 1: Basic setup with OpenMemory only (backward compatibility)
 */
export function createOpenMemoryOnlyClient() {
  const config = CONFIG_PRESETS.openMemoryOnly();
  return new UnifiedAPIClient(config);
}

/**
 * Example 2: Setup with both APIs enabled and auto-fallback
 */
export function createDualAPIClient() {
  const config = createUnifiedAPIConfig({
    openMemoryConfig: {
      baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8765',
    },
    mem0Config: {
      apiKey: process.env.NEXT_PUBLIC_MEM0_API_KEY || 'your-mem0-api-key',
      baseUrl: 'https://api.mem0.ai',
    },
    featureFlags: {
      enableMem0: true,
      enableOpenMemory: true,
      defaultSource: 'mem0',
      enableAutoFallback: true,
      enableCaching: false,
      enableTelemetry: false,
    },
  });
  return new UnifiedAPIClient(config);
}

/**
 * Example 3: Using the unified client with OpenMemory
 */
export async function exampleOpenMemoryUsage(client: UnifiedAPIClient, userId: string) {
  const options: UnifiedMemoryOptions = {
    source: 'openmemory',
    user_id: userId,
    app_name: 'my-app',
  };

  // Create a memory
  const createResult = await client.createMemory('This is a test memory', options);
  console.log('Created memory:', createResult);

  // Search memories
  const searchOptions: UnifiedSearchOptions = {
    ...options,
    query: 'test',
    limit: 10,
  };
  const searchResult = await client.searchMemories('test', searchOptions);
  console.log('Search results:', searchResult);

  return searchResult.data;
}

/**
 * Example 4: Using the unified client with Mem0
 */
export async function exampleMem0Usage(client: UnifiedAPIClient, userId: string) {
  const options: UnifiedMemoryOptions = {
    source: 'mem0',
    user_id: userId,
    version: 'v2',
    infer: true,
  };

  // Create a memory
  const createResult = await client.createMemory('This is a test memory for Mem0', options);
  console.log('Created memory:', createResult);

  // Search with advanced options
  const searchOptions: UnifiedSearchOptions = {
    ...options,
    query: 'test',
    limit: 5,
    keyword_search: true,
    rerank: true,
    threshold: 0.7,
  };
  const searchResult = await client.searchMemories('test', searchOptions);
  console.log('Search results:', searchResult);

  return searchResult.data;
}

/**
 * Example 5: Dynamic source switching
 */
export async function exampleDynamicSwitching(client: UnifiedAPIClient, userId: string) {
  // Start with OpenMemory
  let options: UnifiedMemoryOptions = {
    source: 'openmemory',
    user_id: userId,
  };

  try {
    const openMemoryResult = await client.getMemories(options);
    console.log('OpenMemory result:', openMemoryResult);
  } catch (error) {
    console.log('OpenMemory failed, trying Mem0...');
    
    // Switch to Mem0
    options.source = 'mem0';
    const mem0Result = await client.getMemories(options);
    console.log('Mem0 result:', mem0Result);
  }
}

/**
 * Example 6: Feature flag management
 */
export function exampleFeatureFlagManagement(client: UnifiedAPIClient) {
  // Check current flags
  console.log('Current flags:', client.getFeatureFlags());

  // Check source availability
  console.log('OpenMemory available:', client.isSourceAvailable('openmemory'));
  console.log('Mem0 available:', client.isSourceAvailable('mem0'));

  // Update flags
  client.updateFeatureFlags({
    defaultSource: 'mem0',
    enableAutoFallback: true,
  });

  console.log('Updated flags:', client.getFeatureFlags());
}

/**
 * Example 7: Error handling with fallback
 */
export async function exampleErrorHandlingWithFallback(client: UnifiedAPIClient, userId: string) {
  const options: UnifiedMemoryOptions = {
    source: 'mem0', // Try Mem0 first
    user_id: userId,
  };

  try {
    const result = await client.getMemories(options);
    console.log('Primary source (Mem0) succeeded:', result);
    return result;
  } catch (error) {
    console.log('Primary source failed, auto-fallback should handle this:', error);
    
    // If auto-fallback is enabled, the client will automatically try OpenMemory
    // If not, we can manually try the fallback
    if (!client.getFeatureFlags().enableAutoFallback) {
      options.source = 'openmemory';
      const fallbackResult = await client.getMemories(options);
      console.log('Manual fallback succeeded:', fallbackResult);
      return fallbackResult;
    }
    
    throw error; // Re-throw if no fallback available
  }
}

/**
 * Example 8: Batch operations
 */
export async function exampleBatchOperations(client: UnifiedAPIClient, userId: string) {
  const options: UnifiedMemoryOptions = {
    source: 'mem0', // Mem0 supports batch operations
    user_id: userId,
  };

  // Create multiple memories
  const memories = [
    'First memory content',
    'Second memory content',
    'Third memory content',
  ];

  const createdMemories = [];
  for (const content of memories) {
    const result = await client.createMemory(content, options);
    createdMemories.push(...result.data);
  }

  console.log('Created memories:', createdMemories);

  // Delete multiple memories
  const memoryIds = createdMemories.map(m => m.id);
  await client.deleteMemories(memoryIds, options);
  console.log('Deleted memories:', memoryIds);
}

/**
 * Example 9: Configuration validation
 */
export function exampleConfigValidation() {
  const config = createUnifiedAPIConfig({
    featureFlags: {
      enableMem0: true,
      enableOpenMemory: false,
      defaultSource: 'mem0',
      enableAutoFallback: false,
      enableCaching: false,
      enableTelemetry: false,
    },
    // Missing mem0Config - this should cause validation error
  });

  // This would fail validation because Mem0 is enabled but no config provided
  console.log('Config validation would fail for this configuration');
}

/**
 * Example 10: Migration from legacy API calls
 */
export function exampleMigrationFromLegacy() {
  // Legacy OpenMemory API call pattern
  const legacyApiCall = {
    url: '/api/v1/memories/filter',
    method: 'POST',
    data: {
      user_id: 'user123',
      page: 1,
      size: 10,
      search_query: 'test',
      app_ids: ['app1'],
      category_ids: ['personal'],
    },
  };

  // New unified API call pattern
  const unifiedApiCall: UnifiedSearchOptions = {
    source: 'openmemory', // Maintain backward compatibility
    user_id: 'user123',
    page: 1,
    page_size: 10,
    query: 'test',
    categories: ['personal'],
  };

  console.log('Legacy pattern:', legacyApiCall);
  console.log('Unified pattern:', unifiedApiCall);
  
  // The adapter handles the transformation internally
}

// Export all examples
export const examples = {
  createOpenMemoryOnlyClient,
  createDualAPIClient,
  exampleOpenMemoryUsage,
  exampleMem0Usage,
  exampleDynamicSwitching,
  exampleFeatureFlagManagement,
  exampleErrorHandlingWithFallback,
  exampleBatchOperations,
  exampleConfigValidation,
  exampleMigrationFromLegacy,
};
