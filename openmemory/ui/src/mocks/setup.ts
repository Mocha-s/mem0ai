// MSW Setup and Configuration
import { mockController } from './index';

/**
 * Setup MSW for development environment
 * Call this in your app's entry point (e.g., _app.tsx or layout.tsx)
 */
export async function setupMSW() {
  // Only run in browser environment
  if (typeof window === 'undefined') {
    return;
  }

  // Check if mocking should be enabled
  const isDevelopment = process.env.NODE_ENV === 'development';
  const enableMocking = process.env.NEXT_PUBLIC_ENABLE_MOCKING === 'true';
  
  if (!isDevelopment && !enableMocking) {
    return;
  }

  try {
    // Initialize mock controller
    const initialized = await mockController.initialize();
    
    if (initialized) {
      console.log('🔶 MSW: Successfully initialized for development');
      
      // Log configuration
      const config = mockController.getConfig();
      console.log('🔶 MSW: Configuration:', {
        openMemory: config.openMemory,
        mem0: config.mem0,
        logLevel: config.logLevel,
      });
    } else {
      console.warn('🔶 MSW: Failed to initialize');
    }
  } catch (error) {
    console.error('🔶 MSW: Setup error:', error);
  }
}

/**
 * Setup MSW for testing environment
 * Call this in your test setup file (e.g., jest.setup.js)
 */
export function setupMSWForTesting() {
  const { server } = require('./server');
  
  // Start server before all tests
  beforeAll(() => {
    server.listen({
      onUnhandledRequest: 'error',
    });
  });

  // Reset handlers after each test
  afterEach(() => {
    server.resetHandlers();
  });

  // Stop server after all tests
  afterAll(() => {
    server.close();
  });
}

/**
 * Conditional MSW setup based on environment
 */
export function conditionalSetupMSW() {
  if (typeof window !== 'undefined') {
    // Browser environment
    return setupMSW();
  } else if (typeof global !== 'undefined' && process.env.NODE_ENV === 'test') {
    // Test environment
    return setupMSWForTesting();
  }
}

/**
 * Manual MSW control for development
 */
export function createMSWControls() {
  if (typeof window === 'undefined') {
    return null;
  }

  return {
    start: () => mockController.initialize(),
    stop: () => {
      const { stopMockWorker } = require('./browser');
      stopMockWorker();
    },
    reset: () => {
      const { resetMockHandlers } = require('./browser');
      resetMockHandlers();
    },
    enableOpenMemory: () => {
      const { enableOpenMemoryMocking } = require('./browser');
      enableOpenMemoryMocking();
    },
    enableMem0: () => {
      const { enableMem0Mocking } = require('./browser');
      enableMem0Mocking();
    },
    disable: () => {
      const { disableAllMocking } = require('./browser');
      disableAllMocking();
    },
    getStats: () => {
      const { getMockStats } = require('./browser');
      return getMockStats();
    },
    getConfig: () => mockController.getConfig(),
  };
}

// Export MSW controls for global access in development
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
  (window as any).__MSW_CONTROLS__ = createMSWControls();
  console.log('🔶 MSW: Controls available at window.__MSW_CONTROLS__');
}

// Auto-setup based on environment
if (typeof window !== 'undefined') {
  // Auto-setup in browser
  setupMSW();
} else if (typeof global !== 'undefined' && process.env.NODE_ENV === 'test') {
  // Auto-setup in test environment
  setupMSWForTesting();
}
