// Unified types that bridge OpenMemory and Mem0 systems
import type { Memory as OpenMemoryMemory, Category as OpenMemoryCategory, Client } from '@/components/types';
import type { Memory as Mem0Memory, MemoryOptions, SearchOptions, Message, API_VERSION } from './mem0';

// Unified Memory interface that combines both systems
export interface UnifiedMemory {
  // Common fields
  id: string;
  created_at: string;
  updated_at?: string;
  categories: string[];
  metadata?: Record<string, any>;

  // Content fields (unified)
  content: string; // Unified content field
  memory?: string; // Mem0 specific field
  
  // OpenMemory specific fields
  client?: Client;
  app_name?: string;
  state?: 'active' | 'paused' | 'archived' | 'deleted';

  // Mem0 specific fields
  messages?: Array<Message>;
  event?: string;
  user_id?: string;
  agent_id?: string;
  app_id?: string;
  run_id?: string;
  hash?: string;
  memory_type?: string;
  score?: number;
  owner?: string;
}

// Unified options for memory operations
export interface UnifiedMemoryOptions {
  // Source system identifier
  source?: 'openmemory' | 'mem0';
  
  // Common options
  user_id?: string;
  metadata?: Record<string, any>;
  categories?: string[];
  
  // Mem0 specific options
  version?: API_VERSION | string;
  agent_id?: string;
  app_id?: string;
  run_id?: string;
  infer?: boolean;
  includes?: string;
  excludes?: string;
  custom_categories?: Array<{ name: string; description: string }>;
  custom_instructions?: string;
  timestamp?: number;
  
  // OpenMemory specific options
  client?: Client;
  app_name?: string;
  state?: 'active' | 'paused' | 'archived' | 'deleted';
}

// Unified search options
export interface UnifiedSearchOptions extends UnifiedMemoryOptions {
  // Search specific options
  query?: string;
  limit?: number;
  threshold?: number;
  
  // Mem0 search options
  keyword_search?: boolean;
  rerank?: boolean;
  filter_memories?: boolean;
  retrieval_criteria?: Array<Record<string, any>>;
  top_k?: number;
  fields?: string[];
  
  // Pagination
  page?: number;
  page_size?: number;
}

// Type guards for runtime type checking
export function isOpenMemoryMemory(memory: any): memory is OpenMemoryMemory {
  return memory && typeof memory.client === 'string' && typeof memory.app_name === 'string';
}

export function isMem0Memory(memory: any): memory is Mem0Memory {
  return memory && (memory.user_id !== undefined || memory.agent_id !== undefined || memory.messages !== undefined);
}

export function isUnifiedMemory(memory: any): memory is UnifiedMemory {
  return memory && typeof memory.id === 'string' && typeof memory.content === 'string';
}

// Transformation utilities
export class MemoryTransformer {
  // Convert OpenMemory to Unified format
  static fromOpenMemory(memory: OpenMemoryMemory): UnifiedMemory {
    return {
      id: memory.id,
      content: memory.memory,
      memory: memory.memory,
      created_at: new Date(memory.created_at).toISOString(),
      categories: memory.categories,
      metadata: memory.metadata,
      client: memory.client,
      app_name: memory.app_name,
      state: memory.state,
    };
  }

  // Convert Mem0 to Unified format
  static fromMem0(memory: Mem0Memory): UnifiedMemory {
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

  // Convert Unified to OpenMemory format
  static toOpenMemory(memory: UnifiedMemory): OpenMemoryMemory {
    return {
      id: memory.id,
      memory: memory.content,
      metadata: memory.metadata || {},
      client: memory.client || 'api',
      categories: memory.categories as OpenMemoryCategory[],
      created_at: new Date(memory.created_at).getTime(),
      app_name: memory.app_name || 'unknown',
      state: memory.state || 'active',
    };
  }

  // Convert Unified to Mem0 format
  static toMem0(memory: UnifiedMemory): Mem0Memory {
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
}

// API Response types
export interface UnifiedApiResponse<T = any> {
  data: T;
  message?: string;
  status: 'success' | 'error';
  source: 'openmemory' | 'mem0';
}

export interface UnifiedPaginatedResponse<T = any> {
  data: T[];
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    hasNext: boolean;
    hasPrevious: boolean;
  };
  source: 'openmemory' | 'mem0';
}

// Configuration types
export interface UnifiedConfig {
  defaultSource: 'openmemory' | 'mem0';
  openMemoryConfig?: {
    baseUrl: string;
    apiKey?: string;
  };
  mem0Config?: {
    baseUrl: string;
    apiKey?: string;
    defaultVersion: API_VERSION;
  };
}
