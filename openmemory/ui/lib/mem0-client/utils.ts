// Mem0 API Client utility functions
import type { MemoryOptions, Message } from './types';
import { Mem0APIError } from './types';

/**
 * Validates API key format and presence
 */
export function validateApiKey(apiKey: string): void {
  if (!apiKey) {
    throw new Mem0APIError('Mem0 API key is required');
  }
  if (typeof apiKey !== 'string') {
    throw new Mem0APIError('Mem0 API key must be a string');
  }
  if (apiKey.trim() === '') {
    throw new Mem0APIError('Mem0 API key cannot be empty');
  }
}

/**
 * Validates custom instructions format
 */
export function validateCustomInstructions(instructions?: string): void {
  if (instructions !== undefined) {
    if (typeof instructions !== 'string') {
      throw new Mem0APIError('custom_instructions must be a string');
    }
    if (!instructions.trim()) {
      throw new Mem0APIError('custom_instructions cannot be empty or whitespace-only');
    }
    if (instructions.length > 10000) {
      throw new Mem0APIError('custom_instructions too long (max 10000 characters)');
    }
  }
}

/**
 * Validates organization and project configuration
 */
export function validateOrgProject(
  organizationName?: string | null,
  projectName?: string | null,
  organizationId?: string | number | null,
  projectId?: string | number | null
): void {
  // Check for organizationName/projectName pair
  if (
    (organizationName === null && projectName !== null) ||
    (organizationName !== null && projectName === null)
  ) {
    console.warn(
      'Warning: Both organizationName and projectName must be provided together when using either.'
    );
  }

  // Check for organizationId/projectId pair
  if (
    (organizationId === null && projectId !== null) ||
    (organizationId !== null && projectId === null)
  ) {
    console.warn(
      'Warning: Both organizationId and projectId must be provided together when using either.'
    );
  }
}

/**
 * Prepares request payload by filtering out null/undefined values
 */
export function prepareParams(options: MemoryOptions): Record<string, any> {
  return Object.fromEntries(
    Object.entries(options).filter(([_, v]) => v != null)
  );
}

/**
 * Prepares memory creation payload
 */
export function preparePayload(
  messages: Array<Message>,
  options: MemoryOptions = {}
): Record<string, any> {
  const payload: Record<string, any> = {
    messages,
    ...prepareParams(options),
  };

  // Handle custom instructions validation
  if (payload.custom_instructions) {
    validateCustomInstructions(payload.custom_instructions);
  }

  return payload;
}

/**
 * Builds URL with query parameters
 */
export function buildUrl(baseUrl: string, endpoint: string, params?: Record<string, any>): string {
  const url = new URL(endpoint, baseUrl);
  
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        url.searchParams.append(key, String(value));
      }
    });
  }
  
  return url.toString();
}

/**
 * Determines API version endpoint
 */
export function getVersionEndpoint(version: string, endpoint: string): string {
  const baseEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  return version === 'v2' ? `/v2/${baseEndpoint}` : `/v1/${baseEndpoint}`;
}

/**
 * Handles API response errors
 */
export function handleApiError(error: any): never {
  if (error.response) {
    // Server responded with error status
    const { status, data, statusText } = error.response;
    const message = data?.message || data?.error || statusText || 'API request failed';
    throw new Mem0APIError(message, status, data?.code, data);
  } else if (error.request) {
    // Request was made but no response received
    throw new Mem0APIError('Network error: No response received from server');
  } else {
    // Something else happened
    throw new Mem0APIError(error.message || 'Unknown error occurred');
  }
}

/**
 * Implements exponential backoff for retries
 */
export function calculateRetryDelay(attempt: number, baseDelay: number = 1000): number {
  return Math.min(baseDelay * Math.pow(2, attempt), 30000); // Max 30 seconds
}

/**
 * Checks if error is retryable
 */
export function isRetryableError(error: Mem0APIError): boolean {
  if (!error.status) return false;
  
  // Retry on server errors (5xx) and some client errors
  return (
    error.status >= 500 || // Server errors
    error.status === 429 || // Rate limiting
    error.status === 408 || // Request timeout
    error.status === 409    // Conflict (might be temporary)
  );
}

/**
 * Generates a simple hash for telemetry
 */
export function generateHash(input: string): string {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(36);
}

/**
 * Formats date for API requests
 */
export function formatDateForApi(date: Date | string): string {
  if (typeof date === 'string') {
    return date;
  }
  return date.toISOString();
}

/**
 * Validates memory ID format
 */
export function validateMemoryId(memoryId: string): void {
  if (!memoryId || typeof memoryId !== 'string') {
    throw new Mem0APIError('Memory ID must be a non-empty string');
  }
  if (memoryId.trim() === '') {
    throw new Mem0APIError('Memory ID cannot be empty');
  }
}

/**
 * Validates user ID format
 */
export function validateUserId(userId: string): void {
  if (!userId || typeof userId !== 'string') {
    throw new Mem0APIError('User ID must be a non-empty string');
  }
  if (userId.trim() === '') {
    throw new Mem0APIError('User ID cannot be empty');
  }
}

/**
 * Sanitizes and validates search query
 */
export function sanitizeSearchQuery(query: string): string {
  if (typeof query !== 'string') {
    throw new Mem0APIError('Search query must be a string');
  }
  
  const sanitized = query.trim();
  if (sanitized.length === 0) {
    throw new Mem0APIError('Search query cannot be empty');
  }
  
  if (sanitized.length > 1000) {
    throw new Mem0APIError('Search query too long (max 1000 characters)');
  }
  
  return sanitized;
}

/**
 * Deep clones an object to avoid mutations
 */
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }
  
  if (obj instanceof Date) {
    return new Date(obj.getTime()) as unknown as T;
  }
  
  if (Array.isArray(obj)) {
    return obj.map(item => deepClone(item)) as unknown as T;
  }
  
  const cloned = {} as T;
  for (const key in obj) {
    if (obj.hasOwnProperty(key)) {
      cloned[key] = deepClone(obj[key]);
    }
  }
  
  return cloned;
}
