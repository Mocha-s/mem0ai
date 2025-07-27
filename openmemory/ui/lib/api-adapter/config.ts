// API Adapter Configuration Management
import type { UnifiedAPIClientConfig, FeatureFlags } from './index';

/**
 * Default feature flags configuration
 */
export const DEFAULT_FEATURE_FLAGS: FeatureFlags = {
  enableMem0: false, // Disabled by default for backward compatibility
  enableOpenMemory: true, // Enabled by default
  defaultSource: 'openmemory', // Default to OpenMemory for backward compatibility
  enableAutoFallback: true, // Enable fallback for resilience
  enableCaching: false, // Disabled by default
  enableTelemetry: false, // Disabled by default for privacy
};

/**
 * Environment-based configuration
 */
export function getEnvironmentConfig(): Partial<UnifiedAPIClientConfig> {
  const openMemoryBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8765';
  const mem0ApiKey = process.env.NEXT_PUBLIC_MEM0_API_KEY;
  const mem0BaseUrl = process.env.NEXT_PUBLIC_MEM0_BASE_URL || 'https://api.mem0.ai';
  
  // Feature flags from environment
  const featureFlags: FeatureFlags = {
    enableMem0: process.env.NEXT_PUBLIC_ENABLE_MEM0 === 'true' && !!mem0ApiKey,
    enableOpenMemory: process.env.NEXT_PUBLIC_ENABLE_OPENMEMORY !== 'false', // Default true
    defaultSource: (process.env.NEXT_PUBLIC_DEFAULT_SOURCE as 'openmemory' | 'mem0') || 'openmemory',
    enableAutoFallback: process.env.NEXT_PUBLIC_ENABLE_AUTO_FALLBACK !== 'false', // Default true
    enableCaching: process.env.NEXT_PUBLIC_ENABLE_CACHING === 'true',
    enableTelemetry: process.env.NEXT_PUBLIC_ENABLE_TELEMETRY === 'true',
  };

  const config: Partial<UnifiedAPIClientConfig> = {
    openMemoryConfig: {
      baseUrl: openMemoryBaseUrl,
    },
    featureFlags,
  };

  // Add Mem0 config if API key is available
  if (mem0ApiKey) {
    config.mem0Config = {
      apiKey: mem0ApiKey,
      baseUrl: mem0BaseUrl,
      organizationId: process.env.NEXT_PUBLIC_MEM0_ORG_ID,
      projectId: process.env.NEXT_PUBLIC_MEM0_PROJECT_ID,
    };
  }

  return config;
}

/**
 * Create unified API client configuration
 */
export function createUnifiedAPIConfig(overrides?: Partial<UnifiedAPIClientConfig>): UnifiedAPIClientConfig {
  const envConfig = getEnvironmentConfig();
  const defaultConfig: UnifiedAPIClientConfig = {
    openMemoryConfig: {
      baseUrl: 'http://localhost:8765',
    },
    featureFlags: DEFAULT_FEATURE_FLAGS,
    timeout: 60000,
  };

  // Merge configurations
  const config: UnifiedAPIClientConfig = {
    ...defaultConfig,
    ...envConfig,
    ...overrides,
    featureFlags: {
      ...defaultConfig.featureFlags,
      ...envConfig.featureFlags,
      ...overrides?.featureFlags,
    },
    openMemoryConfig: {
      ...defaultConfig.openMemoryConfig,
      ...envConfig.openMemoryConfig,
      ...overrides?.openMemoryConfig,
    },
  };

  // Add Mem0 config if available
  if (envConfig.mem0Config || overrides?.mem0Config) {
    config.mem0Config = {
      ...envConfig.mem0Config,
      ...overrides?.mem0Config,
    };
  }

  return config;
}

/**
 * Validate configuration
 */
export function validateConfig(config: UnifiedAPIClientConfig): { isValid: boolean; errors: string[] } {
  const errors: string[] = [];

  // Validate OpenMemory config
  if (config.featureFlags.enableOpenMemory) {
    if (!config.openMemoryConfig.baseUrl) {
      errors.push('OpenMemory baseUrl is required when OpenMemory is enabled');
    }
  }

  // Validate Mem0 config
  if (config.featureFlags.enableMem0) {
    if (!config.mem0Config) {
      errors.push('Mem0 config is required when Mem0 is enabled');
    } else {
      if (!config.mem0Config.apiKey) {
        errors.push('Mem0 API key is required when Mem0 is enabled');
      }
    }
  }

  // Validate that at least one source is enabled
  if (!config.featureFlags.enableOpenMemory && !config.featureFlags.enableMem0) {
    errors.push('At least one API source (OpenMemory or Mem0) must be enabled');
  }

  // Validate default source
  if (config.featureFlags.defaultSource === 'mem0' && !config.featureFlags.enableMem0) {
    errors.push('Default source cannot be Mem0 when Mem0 is disabled');
  }
  if (config.featureFlags.defaultSource === 'openmemory' && !config.featureFlags.enableOpenMemory) {
    errors.push('Default source cannot be OpenMemory when OpenMemory is disabled');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Configuration presets for different environments
 */
export const CONFIG_PRESETS = {
  // Development preset - OpenMemory only
  development: (): UnifiedAPIClientConfig => createUnifiedAPIConfig({
    featureFlags: {
      ...DEFAULT_FEATURE_FLAGS,
      enableMem0: false,
      enableOpenMemory: true,
      defaultSource: 'openmemory',
    },
  }),

  // Production preset - Both APIs enabled with fallback
  production: (): UnifiedAPIClientConfig => createUnifiedAPIConfig({
    featureFlags: {
      ...DEFAULT_FEATURE_FLAGS,
      enableMem0: true,
      enableOpenMemory: true,
      defaultSource: 'mem0',
      enableAutoFallback: true,
    },
  }),

  // Mem0 only preset
  mem0Only: (): UnifiedAPIClientConfig => createUnifiedAPIConfig({
    featureFlags: {
      ...DEFAULT_FEATURE_FLAGS,
      enableMem0: true,
      enableOpenMemory: false,
      defaultSource: 'mem0',
      enableAutoFallback: false,
    },
  }),

  // OpenMemory only preset (backward compatibility)
  openMemoryOnly: (): UnifiedAPIClientConfig => createUnifiedAPIConfig({
    featureFlags: {
      ...DEFAULT_FEATURE_FLAGS,
      enableMem0: false,
      enableOpenMemory: true,
      defaultSource: 'openmemory',
      enableAutoFallback: false,
    },
  }),
};

/**
 * Get configuration preset by name
 */
export function getConfigPreset(preset: keyof typeof CONFIG_PRESETS): UnifiedAPIClientConfig {
  return CONFIG_PRESETS[preset]();
}

/**
 * Runtime configuration manager
 */
export class ConfigManager {
  private config: UnifiedAPIClientConfig;
  private listeners: Array<(config: UnifiedAPIClientConfig) => void> = [];

  constructor(initialConfig?: UnifiedAPIClientConfig) {
    this.config = initialConfig || createUnifiedAPIConfig();
  }

  /**
   * Get current configuration
   */
  getConfig(): UnifiedAPIClientConfig {
    return { ...this.config };
  }

  /**
   * Update configuration
   */
  updateConfig(updates: Partial<UnifiedAPIClientConfig>): void {
    this.config = {
      ...this.config,
      ...updates,
      featureFlags: {
        ...this.config.featureFlags,
        ...updates.featureFlags,
      },
      openMemoryConfig: {
        ...this.config.openMemoryConfig,
        ...updates.openMemoryConfig,
      },
      mem0Config: {
        ...this.config.mem0Config,
        ...updates.mem0Config,
      },
    };

    // Notify listeners
    this.listeners.forEach(listener => listener(this.config));
  }

  /**
   * Update feature flags only
   */
  updateFeatureFlags(flags: Partial<FeatureFlags>): void {
    this.updateConfig({ featureFlags: flags });
  }

  /**
   * Subscribe to configuration changes
   */
  subscribe(listener: (config: UnifiedAPIClientConfig) => void): () => void {
    this.listeners.push(listener);
    
    // Return unsubscribe function
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  /**
   * Validate current configuration
   */
  validate(): { isValid: boolean; errors: string[] } {
    return validateConfig(this.config);
  }
}

// Export singleton instance
export const configManager = new ConfigManager();
