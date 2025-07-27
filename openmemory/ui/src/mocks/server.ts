// MSW Server Configuration (for Node.js/Testing)
import { setupServer } from 'msw/node';
import { openMemoryHandlers } from './handlers/openmemory';
import { mem0Handlers } from './handlers/mem0';

// Combine all handlers
const handlers = [
  ...openMemoryHandlers,
  ...mem0Handlers,
];

// Create the server instance
export const server = setupServer(...handlers);

// Server lifecycle management
export function startMockServer() {
  try {
    server.listen({
      onUnhandledRequest: 'warn',
    });
    console.log('🔶 MSW: Mock API server started');
  } catch (error) {
    console.error('Failed to start MSW server:', error);
  }
}

export function stopMockServer() {
  server.close();
  console.log('🔶 MSW: Mock API server stopped');
}

export function resetMockServer() {
  server.resetHandlers();
  console.log('🔶 MSW: Mock API server reset');
}

// Handler management
export function addServerHandler(handler: any) {
  server.use(handler);
}

export function resetServerHandlers() {
  server.resetHandlers(...handlers);
  console.log('🔶 MSW: Server handlers reset to default');
}

// Environment-specific configuration
export function configureServerForTesting() {
  // Reset handlers before each test
  beforeEach(() => {
    server.resetHandlers();
  });

  // Start server before all tests
  beforeAll(() => {
    startMockServer();
  });

  // Stop server after all tests
  afterAll(() => {
    stopMockServer();
  });
}

// Selective API mocking for server
export function enableOpenMemoryServerMocking() {
  server.use(...openMemoryHandlers);
  console.log('🔶 MSW: OpenMemory server mocking enabled');
}

export function enableMem0ServerMocking() {
  server.use(...mem0Handlers);
  console.log('🔶 MSW: Mem0 server mocking enabled');
}

export function disableAllServerMocking() {
  server.resetHandlers();
  console.log('🔶 MSW: All server mocking disabled');
}

// Test utilities
export function createTestServer(customHandlers: any[] = []) {
  const testHandlers = [...handlers, ...customHandlers];
  return setupServer(...testHandlers);
}

export function getServerStats() {
  return {
    totalHandlers: handlers.length,
    openMemoryHandlers: openMemoryHandlers.length,
    mem0Handlers: mem0Handlers.length,
    activeHandlers: server.listHandlers().length,
  };
}

// Export server and handlers
export { server as mockServer, handlers as allServerHandlers };
export { openMemoryHandlers, mem0Handlers };
