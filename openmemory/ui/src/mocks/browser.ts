// MSW Browser Configuration
import { setupWorker } from 'msw/browser';
import { openMemoryHandlers } from './handlers/openmemory';
import { mem0Handlers } from './handlers/mem0';

// Combine all handlers
const handlers = [
  ...openMemoryHandlers,
  ...mem0Handlers,
];

// Create the worker instance
export const worker = setupWorker(...handlers);

// Start the worker
export async function startMockWorker() {
  if (typeof window !== 'undefined') {
    try {
      await worker.start({
        onUnhandledRequest: 'warn',
        serviceWorker: {
          url: '/mockServiceWorker.js',
        },
      });
      console.log('🔶 MSW: Mock API worker started');
    } catch (error) {
      console.error('Failed to start MSW worker:', error);
    }
  }
}

// Stop the worker
export function stopMockWorker() {
  if (typeof window !== 'undefined') {
    worker.stop();
    console.log('🔶 MSW: Mock API worker stopped');
  }
}

// Enable/disable specific API mocking
export function enableOpenMemoryMocking() {
  worker.use(...openMemoryHandlers);
  console.log('🔶 MSW: OpenMemory API mocking enabled');
}

export function enableMem0Mocking() {
  worker.use(...mem0Handlers);
  console.log('🔶 MSW: Mem0 API mocking enabled');
}

export function disableAllMocking() {
  worker.resetHandlers();
  console.log('🔶 MSW: All API mocking disabled');
}

// Reset handlers to original state
export function resetMockHandlers() {
  worker.resetHandlers(...handlers);
  console.log('🔶 MSW: Mock handlers reset to default');
}

// Runtime handler management
export function addMockHandler(handler: any) {
  worker.use(handler);
}

export function removeMockHandler() {
  // MSW doesn't have a direct way to remove specific handlers
  // You would need to reset and re-add the ones you want
  console.warn('MSW: Use resetMockHandlers() and re-add desired handlers');
}

// Environment-based configuration
export function configureMockingForEnvironment() {
  const isDevelopment = process.env.NODE_ENV === 'development';
  const enableMocking = process.env.NEXT_PUBLIC_ENABLE_MOCKING === 'true';
  const mockOpenMemory = process.env.NEXT_PUBLIC_MOCK_OPENMEMORY !== 'false';
  const mockMem0 = process.env.NEXT_PUBLIC_MOCK_MEM0 === 'true';

  if (!isDevelopment && !enableMocking) {
    console.log('🔶 MSW: Mocking disabled in production');
    return false;
  }

  const activeHandlers = [];
  
  if (mockOpenMemory) {
    activeHandlers.push(...openMemoryHandlers);
    console.log('🔶 MSW: OpenMemory mocking enabled');
  }
  
  if (mockMem0) {
    activeHandlers.push(...mem0Handlers);
    console.log('🔶 MSW: Mem0 mocking enabled');
  }

  if (activeHandlers.length > 0) {
    worker.use(...activeHandlers);
    return true;
  }

  return false;
}

// Debug utilities
export function logMockHandlers() {
  console.log('🔶 MSW: Active handlers:', handlers.length);
  handlers.forEach((handler, index) => {
    console.log(`  ${index + 1}. ${handler.info.method} ${handler.info.path}`);
  });
}

export function getMockStats() {
  return {
    totalHandlers: handlers.length,
    openMemoryHandlers: openMemoryHandlers.length,
    mem0Handlers: mem0Handlers.length,
    isWorkerActive: worker.listHandlers().length > 0,
  };
}

// Export worker and handlers for external use
export { worker as mockWorker, handlers as allHandlers };
export { openMemoryHandlers, mem0Handlers };
