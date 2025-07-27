// MSW Integration Examples for Next.js
import React, { useEffect, useState } from 'react';
import { setupMSW, createMSWControls } from '../setup';

/**
 * Example: MSW Integration in _app.tsx
 */
export function AppWithMSW({ Component, pageProps }: any) {
  const [mswReady, setMswReady] = useState(false);

  useEffect(() => {
    const initMSW = async () => {
      if (process.env.NODE_ENV === 'development') {
        await setupMSW();
        setMswReady(true);
      } else {
        setMswReady(true);
      }
    };

    initMSW();
  }, []);

  // Show loading screen while MSW is initializing in development
  if (process.env.NODE_ENV === 'development' && !mswReady) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        fontFamily: 'system-ui, sans-serif'
      }}>
        <div>
          <div>🔶 Initializing Mock API...</div>
          <div style={{ fontSize: '0.8em', color: '#666', marginTop: '8px' }}>
            Setting up MSW for development
          </div>
        </div>
      </div>
    );
  }

  return <Component {...pageProps} />;
}

/**
 * Example: MSW Controls Component for Development
 */
export function MSWControls() {
  const [controls, setControls] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [config, setConfig] = useState<any>(null);

  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      const mswControls = createMSWControls();
      setControls(mswControls);
      
      if (mswControls) {
        setStats(mswControls.getStats());
        setConfig(mswControls.getConfig());
      }
    }
  }, []);

  if (!controls || process.env.NODE_ENV !== 'development') {
    return null;
  }

  const handleAction = async (action: string) => {
    try {
      switch (action) {
        case 'start':
          await controls.start();
          break;
        case 'stop':
          controls.stop();
          break;
        case 'reset':
          controls.reset();
          break;
        case 'enableOpenMemory':
          controls.enableOpenMemory();
          break;
        case 'enableMem0':
          controls.enableMem0();
          break;
        case 'disable':
          controls.disable();
          break;
      }
      
      // Update stats after action
      setStats(controls.getStats());
    } catch (error) {
      console.error('MSW Control action failed:', error);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      background: '#f0f0f0',
      border: '1px solid #ccc',
      borderRadius: '8px',
      padding: '16px',
      fontSize: '12px',
      fontFamily: 'monospace',
      zIndex: 9999,
      maxWidth: '300px',
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
        🔶 MSW Controls
      </div>
      
      <div style={{ marginBottom: '8px' }}>
        <strong>Status:</strong> {stats?.isWorkerActive ? '✅ Active' : '❌ Inactive'}
      </div>
      
      <div style={{ marginBottom: '8px' }}>
        <strong>Handlers:</strong> {stats?.totalHandlers || 0}
        <br />
        <small>
          OpenMemory: {stats?.openMemoryHandlers || 0} | 
          Mem0: {stats?.mem0Handlers || 0}
        </small>
      </div>

      <div style={{ marginBottom: '8px' }}>
        <strong>Config:</strong>
        <br />
        <small>
          OpenMemory: {config?.openMemory ? '✅' : '❌'} | 
          Mem0: {config?.mem0 ? '✅' : '❌'}
        </small>
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
        <button onClick={() => handleAction('start')} style={buttonStyle}>
          Start
        </button>
        <button onClick={() => handleAction('stop')} style={buttonStyle}>
          Stop
        </button>
        <button onClick={() => handleAction('reset')} style={buttonStyle}>
          Reset
        </button>
        <button onClick={() => handleAction('disable')} style={buttonStyle}>
          Disable
        </button>
        <button onClick={() => handleAction('enableOpenMemory')} style={buttonStyle}>
          OpenMemory
        </button>
        <button onClick={() => handleAction('enableMem0')} style={buttonStyle}>
          Mem0
        </button>
      </div>
    </div>
  );
}

const buttonStyle = {
  padding: '4px 8px',
  fontSize: '10px',
  border: '1px solid #999',
  borderRadius: '4px',
  background: '#fff',
  cursor: 'pointer',
};

/**
 * Example: Environment Variables Setup
 */
export const MSWEnvironmentExample = `
# .env.local - MSW Configuration

# Enable/disable mocking
NEXT_PUBLIC_ENABLE_MOCKING=true

# Control which APIs to mock
NEXT_PUBLIC_MOCK_OPENMEMORY=true
NEXT_PUBLIC_MOCK_MEM0=false

# MSW configuration
NEXT_PUBLIC_MOCK_LOG_LEVEL=warn
NEXT_PUBLIC_MSW_SERVICE_WORKER_URL=/mockServiceWorker.js

# Disable mocking in production
NEXT_PUBLIC_DISABLE_MOCKING=false
`;

/**
 * Example: Test Setup
 */
export const TestSetupExample = `
// jest.setup.js
import { setupMSWForTesting } from './src/mocks/setup';

// Setup MSW for all tests
setupMSWForTesting();

// Or manual setup
import { server } from './src/mocks/server';

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
`;

/**
 * Example: Custom Handler
 */
export const CustomHandlerExample = `
// Custom handler for specific test
import { http, HttpResponse } from 'msw';
import { server } from './src/mocks/server';

test('handles custom API response', async () => {
  // Override default handler for this test
  server.use(
    http.get('/api/v1/memories/custom', () => {
      return HttpResponse.json({ message: 'Custom response' });
    })
  );

  // Your test code here
});
`;

/**
 * Example: Dynamic Mock Data
 */
export function DynamicMockExample() {
  const [mockData, setMockData] = useState<any>(null);

  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      // Access mock data store
      import('../data/generators').then(({ mockDataStore }) => {
        setMockData({
          openMemoryCount: mockDataStore.getOpenMemoryMemories().length,
          mem0Count: mockDataStore.getMem0Memories().length,
          userCount: mockDataStore.getUsers().length,
        });
      });
    }
  }, []);

  if (!mockData || process.env.NODE_ENV !== 'development') {
    return null;
  }

  return (
    <div style={{
      position: 'fixed',
      top: '20px',
      right: '20px',
      background: '#e8f4fd',
      border: '1px solid #0066cc',
      borderRadius: '8px',
      padding: '12px',
      fontSize: '12px',
      fontFamily: 'system-ui, sans-serif',
      zIndex: 9998,
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
        📊 Mock Data Stats
      </div>
      <div>OpenMemory Memories: {mockData.openMemoryCount}</div>
      <div>Mem0 Memories: {mockData.mem0Count}</div>
      <div>Users: {mockData.userCount}</div>
    </div>
  );
}

/**
 * Example: Usage in Layout Component
 */
export function LayoutWithMSW({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      {process.env.NODE_ENV === 'development' && (
        <>
          <MSWControls />
          <DynamicMockExample />
        </>
      )}
    </>
  );
}
