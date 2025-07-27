// Unified Type System for OpenMemory-UI
// This file serves as the main entry point for all type definitions

// Base types for the application
export interface BaseEntity {
  id: string;
  created_at: string;
  updated_at: string;
}

// API Response types
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  status: 'success' | 'error';
}

export interface PaginatedResponse<T = any> {
  data: T[];
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    hasNext: boolean;
    hasPrevious: boolean;
  };
}

// Error types
export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, any>;
}

// Common utility types
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;

// Export Mem0 types
export * from './mem0';

// Export unified types and transformers
export * from './unified';

// Re-export from components/types.ts for backward compatibility
export * from '@/components/types';
