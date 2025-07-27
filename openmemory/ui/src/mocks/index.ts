// MSW Mocks Entry Point
export * from './browser';
export * from './server';
export * from './data/generators';
export * from './handlers/openmemory';
export * from './handlers/mem0';

// Unified mock management
import { startMockWorker, configureMockingForEnvironment } from './browser';
import { startMockServer } from './server';

/**
 * Initialize mocking based on environment
 */
export async function initializeMocking() {
  const isServer = typeof window === 'undefined';
  const isDevelopment = process.env.NODE_ENV === 'development';
  const enableMocking = process.env.NEXT_PUBLIC_ENABLE_MOCKING === 'true';

  // Only enable mocking in development or when explicitly enabled
  if (!isDevelopment && !enableMocking) {
    console.log('🔶 MSW: Mocking disabled');
    return false;
  }

  try {
    if (isServer) {
      // Server-side (Node.js)
      startMockServer();
      return true;
    } else {
      // Client-side (Browser)
      const mockingEnabled = configureMockingForEnvironment();
      if (mockingEnabled) {
        await startMockWorker();
        return true;
      }
      return false;
    }
  } catch (error) {
    console.error('Failed to initialize mocking:', error);
    return false;
  }
}

/**
 * Check if mocking should be enabled
 */
export function shouldEnableMocking(): boolean {
  const isDevelopment = process.env.NODE_ENV === 'development';
  const enableMocking = process.env.NEXT_PUBLIC_ENABLE_MOCKING === 'true';
  const disableMocking = process.env.NEXT_PUBLIC_DISABLE_MOCKING === 'true';

  if (disableMocking) {
    return false;
  }

  return isDevelopment || enableMocking;
}

/**
 * Get mock configuration from environment
 */
export function getMockConfig() {
  return {
    enabled: shouldEnableMocking(),
    openMemory: process.env.NEXT_PUBLIC_MOCK_OPENMEMORY !== 'false',
    mem0: process.env.NEXT_PUBLIC_MOCK_MEM0 === 'true',
    logLevel: process.env.NEXT_PUBLIC_MOCK_LOG_LEVEL || 'warn',
    serviceWorkerUrl: process.env.NEXT_PUBLIC_MSW_SERVICE_WORKER_URL || '/mockServiceWorker.js',
  };
}

/**
 * Dynamic mock control
 */
export class MockController {
  private static instance: MockController;
  private isInitialized = false;
  private config = getMockConfig();

  static getInstance(): MockController {
    if (!MockController.instance) {
      MockController.instance = new MockController();
    }
    return MockController.instance;
  }

  async initialize(): Promise<boolean> {
    if (this.isInitialized) {
      return true;
    }

    if (!this.config.enabled) {
      console.log('🔶 MSW: Mocking disabled by configuration');
      return false;
    }

    try {
      const success = await initializeMocking();
      this.isInitialized = success;
      return success;
    } catch (error) {
      console.error('🔶 MSW: Failed to initialize:', error);
      return false;
    }
  }

  getConfig() {
    return { ...this.config };
  }

  updateConfig(newConfig: Partial<typeof this.config>) {
    this.config = { ...this.config, ...newConfig };
  }

  isEnabled(): boolean {
    return this.config.enabled && this.isInitialized;
  }
}

// Export singleton instance
export const mockController = MockController.getInstance();

// Auto-initialize in development
if (typeof window !== 'undefined' && shouldEnableMocking()) {
  mockController.initialize().then((success) => {
    if (success) {
      console.log('🔶 MSW: Auto-initialized successfully');
    }
  });
}
