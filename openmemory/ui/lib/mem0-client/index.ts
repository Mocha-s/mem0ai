// Mem0 API Client - Main implementation
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import type {
  Mem0ClientConfig,
  Mem0APIError,
  RequestOptions,
  Mem0Response,
  PaginatedMem0Response,
  BatchUpdateRequest,
  BatchDeleteRequest,
  CreateMemoryPayload,
  UpdateMemoryPayload,
  ClientStats,
  RequestInterceptor,
  ResponseInterceptor,
  ErrorInterceptor,
  EventListener,
  ClientEvent,
  AdvancedClientOptions,
  Memory,
  MemoryOptions,
  SearchOptions,
  Message,
  MemoryHistory,
  User,
  AllUsers,
  Webhook,
  WebhookPayload,
  FeedbackPayload,
  API_VERSION
} from './types';

import {
  validateApiKey,
  validateOrgProject,
  prepareParams,
  preparePayload,
  buildUrl,
  getVersionEndpoint,
  handleApiError,
  calculateRetryDelay,
  isRetryableError,
  generateHash,
  validateMemoryId,
  validateUserId,
  sanitizeSearchQuery,
  deepClone
} from './utils';

/**
 * Mem0 API Client
 * 
 * A comprehensive client for interacting with the Mem0 API.
 * Supports v1 and v2 API versions, automatic retries, error handling,
 * and advanced features like caching and telemetry.
 */
export class Mem0APIClient {
  private apiKey: string;
  private baseUrl: string;
  private organizationName: string | null;
  private projectName: string | null;
  private organizationId: string | number | null;
  private projectId: string | number | null;
  private client: AxiosInstance;
  private telemetryId: string;
  private stats: ClientStats;
  private eventListeners: Map<ClientEvent, EventListener[]>;
  private requestInterceptors: RequestInterceptor[];
  private responseInterceptors: ResponseInterceptor[];
  private errorInterceptors: ErrorInterceptor[];
  private options: AdvancedClientOptions;

  constructor(config: Mem0ClientConfig, advancedOptions: AdvancedClientOptions = {}) {
    // Validate and set configuration
    validateApiKey(config.apiKey);
    
    this.apiKey = config.apiKey;
    this.baseUrl = config.baseUrl || 'https://api.mem0.ai';
    this.organizationName = config.organizationName || null;
    this.projectName = config.projectName || null;
    this.organizationId = config.organizationId || null;
    this.projectId = config.projectId || null;
    this.options = advancedOptions;

    // Initialize stats
    this.stats = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      averageResponseTime: 0,
    };

    // Initialize event system
    this.eventListeners = new Map();
    this.requestInterceptors = [];
    this.responseInterceptors = [];
    this.errorInterceptors = [];

    // Create axios instance
    this.client = axios.create({
      baseURL: this.baseUrl,
      timeout: config.timeout || 60000,
      headers: {
        'Authorization': `Token ${this.apiKey}`,
        'Content-Type': 'application/json',
        'User-Agent': advancedOptions.userAgent || 'Mem0APIClient/1.0.0',
      },
    });

    // Setup interceptors
    this.setupInterceptors();

    // Initialize telemetry
    this.telemetryId = generateHash(this.apiKey);

    // Validate organization/project configuration
    validateOrgProject(
      this.organizationName,
      this.projectName,
      this.organizationId,
      this.projectId
    );

    // Initialize client
    this.initialize();

    this.emit('client:initialized', { config, advancedOptions });
  }

  /**
   * Initialize the client by pinging the server
   */
  private async initialize(): Promise<void> {
    try {
      await this.ping();
    } catch (error) {
      if (this.options.debug) {
        console.warn('Failed to ping server during initialization:', error);
      }
    }
  }

  /**
   * Setup axios interceptors
   */
  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        this.stats.totalRequests++;
        this.emit('request:start', { config });
        return config;
      },
      (error) => {
        this.stats.failedRequests++;
        this.emit('request:error', { error });
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        this.stats.successfulRequests++;
        this.updateAverageResponseTime(response);
        this.emit('request:success', { response });
        return response;
      },
      (error) => {
        this.stats.failedRequests++;
        this.emit('request:error', { error });
        return Promise.reject(error);
      }
    );
  }

  /**
   * Update average response time statistics
   */
  private updateAverageResponseTime(response: AxiosResponse): void {
    const responseTime = response.config.metadata?.endTime - response.config.metadata?.startTime;
    if (responseTime) {
      const totalTime = this.stats.averageResponseTime * (this.stats.successfulRequests - 1);
      this.stats.averageResponseTime = (totalTime + responseTime) / this.stats.successfulRequests;
    }
    this.stats.lastRequestTime = new Date();
  }

  /**
   * Emit events to registered listeners
   */
  private emit(event: ClientEvent, data?: any): void {
    const listeners = this.eventListeners.get(event) || [];
    listeners.forEach(listener => {
      try {
        listener(event, data);
      } catch (error) {
        if (this.options.debug) {
          console.error(`Error in event listener for ${event}:`, error);
        }
      }
    });
  }

  /**
   * Add event listener
   */
  public on(event: ClientEvent, listener: EventListener): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event)!.push(listener);
  }

  /**
   * Remove event listener
   */
  public off(event: ClientEvent, listener: EventListener): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  /**
   * Add request interceptor
   */
  public addRequestInterceptor(interceptor: RequestInterceptor): void {
    this.requestInterceptors.push(interceptor);
  }

  /**
   * Add response interceptor
   */
  public addResponseInterceptor(interceptor: ResponseInterceptor): void {
    this.responseInterceptors.push(interceptor);
  }

  /**
   * Add error interceptor
   */
  public addErrorInterceptor(interceptor: ErrorInterceptor): void {
    this.errorInterceptors.push(interceptor);
  }

  /**
   * Get client statistics
   */
  public getStats(): ClientStats {
    return deepClone(this.stats);
  }

  /**
   * Reset client statistics
   */
  public resetStats(): void {
    this.stats = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      averageResponseTime: 0,
    };
  }

  /**
   * Ping the server to check connectivity and get organization/project info
   */
  public async ping(): Promise<void> {
    try {
      const response = await this.request('/v1/ping/', { method: 'GET' });

      if (!response || typeof response !== 'object') {
        throw new Mem0APIError('Invalid response format from ping endpoint');
      }

      if (response.status !== 'ok') {
        throw new Mem0APIError(response.message || 'API Key is invalid');
      }

      const { org_id, project_id, user_email } = response;

      // Update organization and project IDs if not already set
      if (org_id && !this.organizationId) this.organizationId = org_id;
      if (project_id && !this.projectId) this.projectId = project_id;
      if (user_email) this.telemetryId = user_email;
    } catch (error: any) {
      if (error instanceof Mem0APIError) {
        throw error;
      } else {
        throw new Mem0APIError(
          `Failed to ping server: ${error.message || 'Unknown error'}`
        );
      }
    }
  }

  /**
   * Make HTTP request with error handling and retries
   */
  private async request<T = any>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { method = 'GET', headers = {}, body, params, timeout } = options;

    let config: AxiosRequestConfig = {
      method,
      url: endpoint,
      headers: { ...headers },
      timeout: timeout || this.client.defaults.timeout,
      metadata: { startTime: Date.now() },
    };

    if (body) {
      config.data = body;
    }

    if (params) {
      config.params = params;
    }

    // Apply request interceptors
    for (const interceptor of this.requestInterceptors) {
      const requestOptions = await interceptor({
        method,
        headers: config.headers,
        body: config.data,
        params: config.params,
        timeout: config.timeout,
      });
      config = {
        ...config,
        method: requestOptions.method || method,
        headers: requestOptions.headers || config.headers,
        data: requestOptions.body || config.data,
        params: requestOptions.params || config.params,
        timeout: requestOptions.timeout || config.timeout,
      };
    }

    const retryConfig = this.options.retry || { attempts: 3, delay: 1000, backoff: 'exponential' };
    let lastError: Mem0APIError;

    for (let attempt = 0; attempt <= retryConfig.attempts; attempt++) {
      try {
        config.metadata.endTime = Date.now();
        const response = await this.client.request(config);

        let result = response.data;

        // Apply response interceptors
        for (const interceptor of this.responseInterceptors) {
          const interceptedResponse = await interceptor({
            data: result,
            status: response.status,
            statusText: response.statusText,
            headers: response.headers,
          });
          result = interceptedResponse.data;
        }

        return result;
      } catch (error: any) {
        const apiError = this.createApiError(error);

        // Apply error interceptors
        let processedError = apiError;
        for (const interceptor of this.errorInterceptors) {
          processedError = await interceptor(processedError);
        }

        lastError = processedError;

        // Check if we should retry
        if (
          attempt < retryConfig.attempts &&
          (retryConfig.retryCondition ? retryConfig.retryCondition(apiError) : isRetryableError(apiError))
        ) {
          const delay = retryConfig.backoff === 'exponential'
            ? calculateRetryDelay(attempt, retryConfig.delay)
            : retryConfig.delay;

          this.emit('request:retry', { attempt, delay, error: apiError });

          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }

        throw processedError;
      }
    }

    throw lastError!;
  }

  /**
   * Create standardized API error from axios error
   */
  private createApiError(error: any): Mem0APIError {
    if (error.response) {
      const { status, data, statusText } = error.response;
      const message = data?.message || data?.error || statusText || 'API request failed';
      return new Mem0APIError(message, status, data?.code, data);
    } else if (error.request) {
      return new Mem0APIError('Network error: No response received from server');
    } else {
      return new Mem0APIError(error.message || 'Unknown error occurred');
    }
  }

  /**
   * Prepare options with organization and project information
   */
  private prepareOptionsWithOrgProject(options: MemoryOptions = {}): MemoryOptions {
    const preparedOptions = { ...options };

    // Add organization and project information
    if (this.organizationName && this.projectName) {
      preparedOptions.org_name = this.organizationName;
      preparedOptions.project_name = this.projectName;
    }

    if (this.organizationId && this.projectId) {
      preparedOptions.org_id = this.organizationId;
      preparedOptions.project_id = this.projectId;

      // Remove deprecated fields if using IDs
      delete preparedOptions.org_name;
      delete preparedOptions.project_name;
    }

    return preparedOptions;
  }

  // ============================================================================
  // MEMORY CRUD OPERATIONS
  // ============================================================================

  /**
   * Add new memories from messages
   */
  public async add(messages: Array<Message>, options: MemoryOptions = {}): Promise<Array<Memory>> {
    if (!Array.isArray(messages) || messages.length === 0) {
      throw new Mem0APIError('Messages array is required and cannot be empty');
    }

    // Ensure client is initialized
    if (!this.telemetryId) {
      await this.ping();
    }

    const preparedOptions = this.prepareOptionsWithOrgProject(options);

    // Handle API version
    if (preparedOptions.api_version) {
      preparedOptions.version = preparedOptions.api_version.toString() || 'v2';
    }

    const payload = preparePayload(messages, preparedOptions);

    return this.request<Array<Memory>>('/v1/memories/', {
      method: 'POST',
      body: payload,
    });
  }

  /**
   * Get a specific memory by ID
   */
  public async get(memoryId: string): Promise<Memory> {
    validateMemoryId(memoryId);

    if (!this.telemetryId) {
      await this.ping();
    }

    return this.request<Memory>(`/v1/memories/${memoryId}/`);
  }

  /**
   * Get all memories with optional search and filtering
   */
  public async getAll(options: SearchOptions = {}): Promise<Array<Memory>> {
    if (!this.telemetryId) {
      await this.ping();
    }

    const preparedOptions = this.prepareOptionsWithOrgProject(options);
    const { api_version, page, page_size, ...otherOptions } = preparedOptions;

    let appendedParams = '';
    let paginatedResponse = false;

    if (page && page_size) {
      appendedParams += `page=${page}&page_size=${page_size}`;
      paginatedResponse = true;
    }

    if (api_version === 'v2') {
      const url = paginatedResponse
        ? `/v2/memories/?${appendedParams}`
        : '/v2/memories/';

      return this.request<Array<Memory>>(url, {
        method: 'POST',
        body: otherOptions,
      });
    } else {
      // V1 API
      const url = paginatedResponse
        ? `/v1/memories/?${appendedParams}`
        : '/v1/memories/';

      return this.request<Array<Memory>>(url, {
        method: 'GET',
        params: otherOptions,
      });
    }
  }

  /**
   * Update a memory by ID
   */
  public async update(memoryId: string, text: string): Promise<Array<Memory>> {
    validateMemoryId(memoryId);

    if (!text || typeof text !== 'string') {
      throw new Mem0APIError('Text is required and must be a string');
    }

    if (!this.telemetryId) {
      await this.ping();
    }

    const payload: UpdateMemoryPayload = { text };

    return this.request<Array<Memory>>(`/v1/memories/${memoryId}/`, {
      method: 'PUT',
      body: payload,
    });
  }

  /**
   * Delete a specific memory by ID
   */
  public async delete(memoryId: string): Promise<void> {
    validateMemoryId(memoryId);

    if (!this.telemetryId) {
      await this.ping();
    }

    await this.request<void>(`/v1/memories/${memoryId}/`, {
      method: 'DELETE',
    });
  }

  /**
   * Delete all memories for a user
   */
  public async deleteAll(userId: string): Promise<void> {
    validateUserId(userId);

    if (!this.telemetryId) {
      await this.ping();
    }

    await this.request<void>('/v1/memories/', {
      method: 'DELETE',
      body: { user_id: userId },
    });
  }

  /**
   * Search memories with advanced options
   */
  public async search(query: string, options: SearchOptions = {}): Promise<Array<Memory>> {
    const sanitizedQuery = sanitizeSearchQuery(query);

    if (!this.telemetryId) {
      await this.ping();
    }

    const searchOptions: SearchOptions = {
      ...options,
      query: sanitizedQuery,
    };

    return this.getAll(searchOptions);
  }

  // ============================================================================
  // BATCH OPERATIONS
  // ============================================================================

  /**
   * Batch update multiple memories
   */
  public async batchUpdate(updates: BatchUpdateRequest[]): Promise<Array<Memory>> {
    if (!Array.isArray(updates) || updates.length === 0) {
      throw new Mem0APIError('Updates array is required and cannot be empty');
    }

    // Validate each update request
    updates.forEach((update, index) => {
      if (!update.memory_id || !update.text) {
        throw new Mem0APIError(`Invalid update at index ${index}: memory_id and text are required`);
      }
    });

    if (!this.telemetryId) {
      await this.ping();
    }

    return this.request<Array<Memory>>('/v1/memories/batch/', {
      method: 'PUT',
      body: { updates },
    });
  }

  /**
   * Batch delete multiple memories
   */
  public async batchDelete(memoryIds: string[]): Promise<void> {
    if (!Array.isArray(memoryIds) || memoryIds.length === 0) {
      throw new Mem0APIError('Memory IDs array is required and cannot be empty');
    }

    // Validate each memory ID
    memoryIds.forEach((id, index) => {
      if (!id || typeof id !== 'string') {
        throw new Mem0APIError(`Invalid memory ID at index ${index}`);
      }
    });

    if (!this.telemetryId) {
      await this.ping();
    }

    await this.request<void>('/v1/memories/batch/', {
      method: 'DELETE',
      body: { memory_ids: memoryIds },
    });
  }

  // ============================================================================
  // MEMORY HISTORY
  // ============================================================================

  /**
   * Get memory history for a specific memory
   */
  public async history(memoryId: string): Promise<Array<MemoryHistory>> {
    validateMemoryId(memoryId);

    if (!this.telemetryId) {
      await this.ping();
    }

    return this.request<Array<MemoryHistory>>(`/v1/memories/${memoryId}/history/`);
  }

  // ============================================================================
  // USER MANAGEMENT
  // ============================================================================

  /**
   * Get all users
   */
  public async getUsers(): Promise<AllUsers> {
    if (!this.telemetryId) {
      await this.ping();
    }

    return this.request<AllUsers>('/v1/users/');
  }

  /**
   * Delete users by IDs
   */
  public async deleteUsers(userIds: string[]): Promise<void> {
    if (!Array.isArray(userIds) || userIds.length === 0) {
      throw new Mem0APIError('User IDs array is required and cannot be empty');
    }

    userIds.forEach((id, index) => {
      if (!id || typeof id !== 'string') {
        throw new Mem0APIError(`Invalid user ID at index ${index}`);
      }
    });

    if (!this.telemetryId) {
      await this.ping();
    }

    await this.request<void>('/v1/users/', {
      method: 'DELETE',
      body: { user_ids: userIds },
    });
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  /**
   * Get API version endpoint
   */
  public getVersionEndpoint(version: API_VERSION, endpoint: string): string {
    return getVersionEndpoint(version, endpoint);
  }

  /**
   * Destroy the client and clean up resources
   */
  public destroy(): void {
    this.eventListeners.clear();
    this.requestInterceptors.length = 0;
    this.responseInterceptors.length = 0;
    this.errorInterceptors.length = 0;
    this.emit('client:destroyed');
  }
}

// Export the client class and types
export default Mem0APIClient;
export { Mem0APIClient };
export * from './types';
export * from './utils';
