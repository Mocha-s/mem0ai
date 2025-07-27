// Mem0 API Types - Based on mem0-ts/src/client/mem0.types.ts

// Common interface for project and organization
interface Common {
  project_id?: string | null;
  org_id?: string | null;
}

// API Version enum
export enum API_VERSION {
  V1 = 'v1',
  V2 = 'v2',
}

// Output format enum
export enum OutputFormat {
  V1 = 'v1.0',
  V1_1 = 'v1.1',
}

// Event types for memory operations
export enum Event {
  ADD = 'ADD',
  UPDATE = 'UPDATE',
  DELETE = 'DELETE',
  NOOP = 'NOOP',
}

// Feedback types
export enum Feedback {
  POSITIVE = 'POSITIVE',
  NEGATIVE = 'NEGATIVE',
  VERY_NEGATIVE = 'VERY_NEGATIVE',
}

// Webhook events
export enum WebhookEvent {
  MEMORY_ADDED = 'memory_add',
  MEMORY_UPDATED = 'memory_update',
  MEMORY_DELETED = 'memory_delete',
}

// Custom categories interface
interface CustomCategories {
  [key: string]: any;
}

// Multi-modal message content
export interface MultiModalMessages {
  type: 'image_url' | 'mdx_url' | 'pdf_url';
  image_url?: {
    url: string;
  };
  mdx_url?: {
    url: string;
  };
  pdf_url?: {
    url: string;
  };
}

// Message interface for conversations
export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string | MultiModalMessages;
}

// Legacy Messages interface for backward compatibility
export interface Messages extends Message {}

// Memory options for API calls
export interface MemoryOptions {
  api_version?: API_VERSION | string;
  version?: API_VERSION | string;
  user_id?: string;
  agent_id?: string;
  app_id?: string;
  run_id?: string;
  metadata?: Record<string, any>;
  filters?: Record<string, any>;
  org_name?: string | null; // Deprecated
  project_name?: string | null; // Deprecated
  org_id?: string | number | null;
  project_id?: string | number | null;
  infer?: boolean;
  page?: number;
  page_size?: number;
  includes?: string;
  excludes?: string;
  enable_graph?: boolean;
  start_date?: string;
  end_date?: string;
  custom_categories?: CustomCategories[];
  custom_instructions?: string;
  timestamp?: number;
  output_format?: string | OutputFormat;
  async_mode?: boolean;
  filter_memories?: boolean;
  immutable?: boolean;
  structured_data_schema?: Record<string, any>;
}

// Search options extending memory options
export interface SearchOptions extends MemoryOptions {
  limit?: number;
  threshold?: number;
  top_k?: number;
  only_metadata_based_search?: boolean;
  keyword_search?: boolean;
  fields?: string[];
  categories?: string[];
  rerank?: boolean;
  retrieval_criteria?: Array<Record<string, any>>;
}

// Memory data structure
export interface MemoryData {
  memory: string;
}

// Core Memory interface
export interface Memory {
  id: string;
  messages?: Array<Message>;
  event?: Event | string;
  data?: MemoryData | null;
  memory?: string;
  user_id?: string;
  hash?: string;
  categories?: Array<string>;
  created_at?: string | Date;
  updated_at?: string | Date;
  memory_type?: string;
  score?: number;
  metadata?: any | null;
  owner?: string | null;
  agent_id?: string | null;
  app_id?: string | null;
  run_id?: string | null;
}

// Memory history interface
export interface MemoryHistory {
  id: string;
  memory_id: string;
  input: Array<Message>;
  old_memory: string | null;
  new_memory: string | null;
  user_id: string;
  categories: Array<string>;
  event: Event | string;
  created_at: string | Date;
  updated_at: string | Date;
}

// Memory update body for batch operations
export interface MemoryUpdateBody {
  memoryId: string;
  text: string;
}

// User interface
export interface User {
  id: string;
  name: string;
  created_at: string | Date;
  updated_at: string | Date;
  total_memories: number;
  owner: string;
  type: string;
}

// All users response
export interface AllUsers {
  count: number;
  results: Array<User>;
  next: any;
  previous: any;
}

// Project options
export interface ProjectOptions {
  fields?: string[];
}

// Project response
export interface ProjectResponse {
  custom_instructions?: string;
  custom_categories?: string[];
  [key: string]: any;
}

// Prompt update payload
export interface PromptUpdatePayload {
  custom_instructions?: string;
  custom_categories?: CustomCategories[];
  [key: string]: any;
}

// Webhook interface
export interface Webhook {
  webhook_id?: string;
  name: string;
  url: string;
  project?: string;
  created_at?: string | Date;
  updated_at?: string | Date;
  is_active?: boolean;
  event_types?: WebhookEvent[];
}

// Webhook payload
export interface WebhookPayload {
  eventTypes: WebhookEvent[];
  projectId: string;
  webhookId: string;
  name: string;
  url: string;
}

// Feedback payload
export interface FeedbackPayload {
  memory_id: string;
  feedback?: Feedback | null;
  feedback_reason?: string | null;
}

// Memory export payloads
export interface CreateMemoryExportPayload extends Common {
  schema: Record<string, any>;
  filters: Record<string, any>;
  export_instructions?: string;
}

export interface GetMemoryExportPayload extends Common {
  filters?: Record<string, any>;
  memory_export_id?: string;
}
