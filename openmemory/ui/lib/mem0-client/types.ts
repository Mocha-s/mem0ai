// Mem0 API Client specific types
import type { 
  MemoryOptions, 
  SearchOptions, 
  Memory, 
  Message, 
  API_VERSION,
  MemoryHistory,
  User,
  AllUsers,
  Webhook,
  WebhookPayload,
  FeedbackPayload,
  CreateMemoryExportPayload,
  GetMemoryExportPayload
} from '@/lib/types/mem0';

// Client configuration interface
export interface Mem0ClientConfig {
  apiKey: string;
  baseUrl?: string;
  organizationName?: string;
  projectName?: string;
  organizationId?: string | number;
  projectId?: string | number;
  timeout?: number;
  retryAttempts?: number;
  retryDelay?: number;
}

// API Error class
export class Mem0APIError extends Error {
  public status?: number;
  public code?: string;
  public details?: any;

  constructor(message: string, status?: number, code?: string, details?: any) {
    super(message);
    this.name = 'Mem0APIError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// Request options interface
export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  headers?: Record<string, string>;
  body?: any;
  params?: Record<string, any>;
  timeout?: number;
}

// Response wrapper interface
export interface Mem0Response<T = any> {
  data: T;
  status: number;
  statusText: string;
  headers: Record<string, string>;
}

// Paginated response interface
export interface PaginatedMem0Response<T = any> {
  results: T[];
  count: number;
  next: string | null;
  previous: string | null;
}

// Batch operation interfaces
export interface BatchUpdateRequest {
  memory_id: string;
  text: string;
}

export interface BatchDeleteRequest {
  memory_ids: string[];
}

// Search result interface
export interface SearchResult extends Memory {
  score?: number;
  relevance?: number;
}

// Memory creation payload
export interface CreateMemoryPayload {
  messages: Array<Message>;
  options?: MemoryOptions;
}

// Memory update payload
export interface UpdateMemoryPayload {
  text: string;
}

// Client statistics interface
export interface ClientStats {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  averageResponseTime: number;
  lastRequestTime?: Date;
}

// Request interceptor function type
export type RequestInterceptor = (config: RequestOptions) => RequestOptions | Promise<RequestOptions>;

// Response interceptor function type
export type ResponseInterceptor = <T>(response: Mem0Response<T>) => Mem0Response<T> | Promise<Mem0Response<T>>;

// Error interceptor function type
export type ErrorInterceptor = (error: Mem0APIError) => Mem0APIError | Promise<Mem0APIError>;

// Client event types
export type ClientEvent = 
  | 'request:start'
  | 'request:success'
  | 'request:error'
  | 'request:retry'
  | 'client:initialized'
  | 'client:destroyed';

// Event listener function type
export type EventListener = (event: ClientEvent, data?: any) => void;

// Retry configuration
export interface RetryConfig {
  attempts: number;
  delay: number;
  backoff: 'linear' | 'exponential';
  retryCondition?: (error: Mem0APIError) => boolean;
}

// Cache configuration
export interface CacheConfig {
  enabled: boolean;
  ttl: number; // Time to live in milliseconds
  maxSize: number; // Maximum number of cached items
}

// Advanced client options
export interface AdvancedClientOptions {
  retry?: RetryConfig;
  cache?: CacheConfig;
  telemetry?: boolean;
  debug?: boolean;
  userAgent?: string;
}

// Export all types from mem0 types for convenience
export type {
  MemoryOptions,
  SearchOptions,
  Memory,
  Message,
  API_VERSION,
  MemoryHistory,
  User,
  AllUsers,
  Webhook,
  WebhookPayload,
  FeedbackPayload,
  CreateMemoryExportPayload,
  GetMemoryExportPayload
};
