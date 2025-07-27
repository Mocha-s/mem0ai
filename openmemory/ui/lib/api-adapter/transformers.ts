// Data transformation functions for API adapter
import type { 
  Memory as OpenMemoryMemory, 
  Category as OpenMemoryCategory,
  Client as OpenMemoryClient 
} from '@/components/types';
import type { 
  Memory as Mem0Memory, 
  MemoryOptions, 
  SearchOptions, 
  Message 
} from '@/lib/types/mem0';
import type { 
  UnifiedMemory, 
  UnifiedMemoryOptions, 
  UnifiedSearchOptions 
} from '@/lib/types/unified';

// ============================================================================
// OPENMEMORY TRANSFORMERS
// ============================================================================

/**
 * Transform OpenMemory API response to UnifiedMemory format
 */
export function transformOpenMemoryToUnified(memory: any): UnifiedMemory {
  return {
    id: memory.id,
    content: memory.content || memory.memory,
    memory: memory.content || memory.memory,
    created_at: typeof memory.created_at === 'number' 
      ? new Date(memory.created_at).toISOString()
      : memory.created_at,
    updated_at: memory.updated_at ? 
      (typeof memory.updated_at === 'number' 
        ? new Date(memory.updated_at).toISOString()
        : memory.updated_at) 
      : undefined,
    categories: memory.categories || [],
    metadata: memory.metadata_ || memory.metadata || {},
    client: memory.client || 'api',
    app_name: memory.app_name,
    state: memory.state,
  };
}

/**
 * Transform OpenMemory API response array to UnifiedMemory array
 */
export function transformOpenMemoryArrayToUnified(memories: any[]): UnifiedMemory[] {
  return memories.map(transformOpenMemoryToUnified);
}

/**
 * Transform UnifiedMemory to OpenMemory API format
 */
export function transformUnifiedToOpenMemory(memory: UnifiedMemory): OpenMemoryMemory {
  return {
    id: memory.id,
    memory: memory.content,
    metadata: memory.metadata || {},
    client: (memory.client as OpenMemoryClient) || 'api',
    categories: memory.categories as OpenMemoryCategory[],
    created_at: new Date(memory.created_at).getTime(),
    app_name: memory.app_name || 'unknown',
    state: memory.state || 'active',
  };
}

// ============================================================================
// MEM0 TRANSFORMERS
// ============================================================================

/**
 * Transform Mem0 Memory to UnifiedMemory format
 */
export function transformMem0ToUnified(memory: Mem0Memory): UnifiedMemory {
  return {
    id: memory.id,
    content: memory.memory || '',
    memory: memory.memory,
    created_at: typeof memory.created_at === 'string' 
      ? memory.created_at 
      : memory.created_at?.toISOString() || new Date().toISOString(),
    updated_at: typeof memory.updated_at === 'string'
      ? memory.updated_at
      : memory.updated_at?.toISOString(),
    categories: memory.categories || [],
    metadata: memory.metadata,
    messages: memory.messages,
    event: memory.event,
    user_id: memory.user_id,
    agent_id: memory.agent_id,
    app_id: memory.app_id,
    run_id: memory.run_id,
    hash: memory.hash,
    memory_type: memory.memory_type,
    score: memory.score,
    owner: memory.owner,
  };
}

/**
 * Transform Mem0 Memory array to UnifiedMemory array
 */
export function transformMem0ArrayToUnified(memories: Mem0Memory[]): UnifiedMemory[] {
  return memories.map(transformMem0ToUnified);
}

/**
 * Transform UnifiedMemory to Mem0 format
 */
export function transformUnifiedToMem0(memory: UnifiedMemory): Mem0Memory {
  return {
    id: memory.id,
    memory: memory.content,
    messages: memory.messages,
    event: memory.event,
    created_at: memory.created_at,
    updated_at: memory.updated_at,
    categories: memory.categories,
    metadata: memory.metadata,
    user_id: memory.user_id,
    agent_id: memory.agent_id,
    app_id: memory.app_id,
    run_id: memory.run_id,
    hash: memory.hash,
    memory_type: memory.memory_type,
    score: memory.score,
    owner: memory.owner,
  };
}

// ============================================================================
// OPTIONS TRANSFORMERS
// ============================================================================

/**
 * Transform UnifiedMemoryOptions to OpenMemory API parameters
 */
export function transformUnifiedToOpenMemoryOptions(options: UnifiedMemoryOptions): any {
  const openMemoryOptions: any = {};

  // Map common fields
  if (options.user_id) openMemoryOptions.user_id = options.user_id;
  if (options.categories) openMemoryOptions.categories = options.categories;
  if (options.metadata) openMemoryOptions.metadata = options.metadata;

  // Map OpenMemory specific fields
  if (options.client) openMemoryOptions.client = options.client;
  if (options.app_name) openMemoryOptions.app_name = options.app_name;
  if (options.state) openMemoryOptions.state = options.state;

  return openMemoryOptions;
}

/**
 * Transform UnifiedSearchOptions to OpenMemory API parameters
 */
export function transformUnifiedToOpenMemorySearchOptions(options: UnifiedSearchOptions): any {
  const searchOptions: any = transformUnifiedToOpenMemoryOptions(options);

  // Add search specific fields
  if (options.query) searchOptions.search_query = options.query;
  if (options.limit) searchOptions.size = options.limit;
  if (options.page) searchOptions.page = options.page;

  return searchOptions;
}

/**
 * Transform UnifiedMemoryOptions to Mem0 MemoryOptions
 */
export function transformUnifiedToMem0Options(options: UnifiedMemoryOptions): MemoryOptions {
  const mem0Options: MemoryOptions = {};

  // Map common fields
  if (options.user_id) mem0Options.user_id = options.user_id;
  if (options.categories) mem0Options.custom_categories = options.categories.map(cat => ({ name: cat, description: cat }));
  if (options.metadata) mem0Options.metadata = options.metadata;

  // Map Mem0 specific fields
  if (options.version) mem0Options.version = options.version;
  if (options.agent_id) mem0Options.agent_id = options.agent_id;
  if (options.app_id) mem0Options.app_id = options.app_id;
  if (options.run_id) mem0Options.run_id = options.run_id;
  if (options.infer !== undefined) mem0Options.infer = options.infer;
  if (options.includes) mem0Options.includes = options.includes;
  if (options.excludes) mem0Options.excludes = options.excludes;
  if (options.custom_instructions) mem0Options.custom_instructions = options.custom_instructions;
  if (options.timestamp) mem0Options.timestamp = options.timestamp;

  return mem0Options;
}

/**
 * Transform UnifiedSearchOptions to Mem0 SearchOptions
 */
export function transformUnifiedToMem0SearchOptions(options: UnifiedSearchOptions): SearchOptions {
  const searchOptions: SearchOptions = transformUnifiedToMem0Options(options);

  // Add search specific fields
  if (options.limit) searchOptions.limit = options.limit;
  if (options.threshold) searchOptions.threshold = options.threshold;
  if (options.keyword_search !== undefined) searchOptions.keyword_search = options.keyword_search;
  if (options.rerank !== undefined) searchOptions.rerank = options.rerank;
  if (options.filter_memories !== undefined) searchOptions.filter_memories = options.filter_memories;
  if (options.retrieval_criteria) searchOptions.retrieval_criteria = options.retrieval_criteria;
  if (options.top_k) searchOptions.top_k = options.top_k;
  if (options.fields) searchOptions.fields = options.fields;
  if (options.page) searchOptions.page = options.page;
  if (options.page_size) searchOptions.page_size = options.page_size;

  return searchOptions;
}

// ============================================================================
// MESSAGE TRANSFORMERS
// ============================================================================

/**
 * Transform text content to Mem0 Message format
 */
export function transformTextToMem0Message(text: string, role: 'user' | 'assistant' | 'system' = 'user'): Message {
  return {
    role,
    content: text,
  };
}

/**
 * Transform OpenMemory memory content to Mem0 Messages array
 */
export function transformOpenMemoryContentToMem0Messages(content: string): Message[] {
  return [transformTextToMem0Message(content)];
}

// ============================================================================
// RESPONSE TRANSFORMERS
// ============================================================================

/**
 * Transform OpenMemory API response to unified format
 */
export function transformOpenMemoryResponse(response: any): {
  memories: UnifiedMemory[];
  total?: number;
  page?: number;
  pages?: number;
} {
  const memories = Array.isArray(response.items) 
    ? transformOpenMemoryArrayToUnified(response.items)
    : Array.isArray(response) 
      ? transformOpenMemoryArrayToUnified(response)
      : [transformOpenMemoryToUnified(response)];

  return {
    memories,
    total: response.total,
    page: response.page,
    pages: response.pages,
  };
}

/**
 * Transform Mem0 API response to unified format
 */
export function transformMem0Response(response: Mem0Memory[] | Mem0Memory): {
  memories: UnifiedMemory[];
  total?: number;
  page?: number;
  pages?: number;
} {
  const memories = Array.isArray(response) 
    ? transformMem0ArrayToUnified(response)
    : [transformMem0ToUnified(response)];

  return {
    memories,
    // Mem0 doesn't provide pagination info in the same format
    total: memories.length,
    page: 1,
    pages: 1,
  };
}
