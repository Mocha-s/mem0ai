// OpenMemory API Mock Handlers
import { http, HttpResponse } from 'msw';
import {
  generateOpenMemoryMemory,
  generateOpenMemoryMemories,
  generateOpenMemoryApiResponse,
  generateOpenMemorySimpleMemory,
  mockDataStore,
} from '../data/generators';
import type { Memory as OpenMemoryMemory } from '@/components/types';

// ============================================================================
// MEMORY ENDPOINTS
// ============================================================================

/**
 * POST /api/v1/memories/filter - Filter and search memories
 */
const filterMemories = http.post('/api/v1/memories/filter', async ({ request }) => {
  const body = await request.json() as any;
  const { 
    user_id, 
    page = 1, 
    size = 10, 
    search_query, 
    app_ids, 
    category_ids, 
    sort_column, 
    sort_direction, 
    show_archived 
  } = body;

  let memories = mockDataStore.getOpenMemoryMemories();

  // Filter by search query
  if (search_query) {
    memories = memories.filter(memory => 
      memory.memory.toLowerCase().includes(search_query.toLowerCase())
    );
  }

  // Filter by app_ids
  if (app_ids && app_ids.length > 0) {
    memories = memories.filter(memory => app_ids.includes(memory.app_name));
  }

  // Filter by category_ids
  if (category_ids && category_ids.length > 0) {
    memories = memories.filter(memory => 
      memory.categories.some(cat => category_ids.includes(cat))
    );
  }

  // Filter by archived state
  if (!show_archived) {
    memories = memories.filter(memory => memory.state !== 'archived');
  }

  // Sort memories
  if (sort_column) {
    memories.sort((a, b) => {
      let aValue: any, bValue: any;
      
      switch (sort_column) {
        case 'created_at':
          aValue = a.created_at;
          bValue = b.created_at;
          break;
        case 'memory':
          aValue = a.memory;
          bValue = b.memory;
          break;
        default:
          aValue = a.created_at;
          bValue = b.created_at;
      }

      if (sort_direction === 'desc') {
        return bValue > aValue ? 1 : -1;
      } else {
        return aValue > bValue ? 1 : -1;
      }
    });
  }

  // Paginate
  const startIndex = (page - 1) * size;
  const endIndex = startIndex + size;
  const paginatedMemories = memories.slice(startIndex, endIndex);

  // Transform to API response format
  const items = paginatedMemories.map(memory => ({
    id: memory.id,
    content: memory.memory,
    created_at: new Date(memory.created_at).toISOString(),
    state: memory.state,
    app_id: memory.app_name,
    categories: memory.categories,
    metadata_: memory.metadata,
    app_name: memory.app_name,
  }));

  return HttpResponse.json({
    items,
    total: memories.length,
    page,
    size,
    pages: Math.ceil(memories.length / size),
  });
});

/**
 * POST /api/v1/memories/ - Create a new memory
 */
const createMemory = http.post('/api/v1/memories/', async ({ request }) => {
  const body = await request.json() as any;
  const { user_id, text, infer, app } = body;

  const newMemory = generateOpenMemoryMemory({
    memory: text,
    app_name: app || 'openmemory',
    state: 'active',
  });

  mockDataStore.addOpenMemoryMemory(newMemory);

  return HttpResponse.json({
    id: newMemory.id,
    content: newMemory.memory,
    created_at: new Date(newMemory.created_at).toISOString(),
    state: newMemory.state,
    app_id: newMemory.app_name,
    categories: newMemory.categories,
    metadata_: newMemory.metadata,
    app_name: newMemory.app_name,
  });
});

/**
 * GET /api/v1/memories/:id - Get a specific memory
 */
const getMemory = http.get('/api/v1/memories/:id', ({ params, request }) => {
  const { id } = params;
  const url = new URL(request.url);
  const user_id = url.searchParams.get('user_id');

  const memory = mockDataStore.getOpenMemoryMemory(id as string);
  
  if (!memory) {
    return HttpResponse.json(
      { error: 'Memory not found' },
      { status: 404 }
    );
  }

  return HttpResponse.json({
    id: memory.id,
    text: memory.memory,
    created_at: new Date(memory.created_at).toISOString(),
    state: memory.state,
    categories: memory.categories,
    app_name: memory.app_name,
  });
});

/**
 * PUT /api/v1/memories/:id - Update a memory
 */
const updateMemory = http.put('/api/v1/memories/:id', async ({ params, request }) => {
  const { id } = params;
  const body = await request.json() as any;
  const { memory_content, user_id } = body;

  const updatedMemory = mockDataStore.updateOpenMemoryMemory(id as string, {
    memory: memory_content,
  });

  if (!updatedMemory) {
    return HttpResponse.json(
      { error: 'Memory not found' },
      { status: 404 }
    );
  }

  return HttpResponse.json({
    id: updatedMemory.id,
    content: updatedMemory.memory,
    created_at: new Date(updatedMemory.created_at).toISOString(),
    state: updatedMemory.state,
    app_id: updatedMemory.app_name,
    categories: updatedMemory.categories,
    metadata_: updatedMemory.metadata,
    app_name: updatedMemory.app_name,
  });
});

/**
 * DELETE /api/v1/memories/ - Delete memories
 */
const deleteMemories = http.delete('/api/v1/memories/', async ({ request }) => {
  const body = await request.json() as any;
  const { memory_ids, user_id } = body;

  memory_ids.forEach((id: string) => {
    mockDataStore.deleteOpenMemoryMemory(id);
  });

  return HttpResponse.json({ success: true });
});

/**
 * GET /api/v1/memories/:id/access-log - Get memory access logs
 */
const getMemoryAccessLogs = http.get('/api/v1/memories/:id/access-log', ({ params, request }) => {
  const { id } = params;
  const url = new URL(request.url);
  const page = parseInt(url.searchParams.get('page') || '1');
  const page_size = parseInt(url.searchParams.get('page_size') || '10');

  // Generate mock access logs
  const logs = Array.from({ length: 20 }, (_, index) => ({
    id: `log-${index + 1}`,
    app_name: `app-${Math.floor(Math.random() * 5) + 1}`,
    accessed_at: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString(),
  }));

  const startIndex = (page - 1) * page_size;
  const endIndex = startIndex + page_size;
  const paginatedLogs = logs.slice(startIndex, endIndex);

  return HttpResponse.json({
    total: logs.length,
    page,
    page_size,
    logs: paginatedLogs,
  });
});

/**
 * GET /api/v1/memories/:id/related - Get related memories
 */
const getRelatedMemories = http.get('/api/v1/memories/:id/related', ({ params, request }) => {
  const { id } = params;
  const url = new URL(request.url);
  const user_id = url.searchParams.get('user_id');

  const relatedMemories = generateOpenMemoryMemories(5);
  
  const items = relatedMemories.map(memory => ({
    id: memory.id,
    content: memory.memory,
    created_at: memory.created_at,
    state: memory.state,
    app_id: memory.app_name,
    app_name: memory.app_name,
    categories: memory.categories,
    metadata_: memory.metadata,
  }));

  return HttpResponse.json({
    items,
    total: items.length,
    page: 1,
    size: items.length,
    pages: 1,
  });
});

/**
 * POST /api/v1/memories/actions/pause - Update memory state
 */
const updateMemoryState = http.post('/api/v1/memories/actions/pause', async ({ request }) => {
  const body = await request.json() as any;
  const { memory_ids, state, user_id } = body;

  memory_ids.forEach((id: string) => {
    mockDataStore.updateOpenMemoryMemory(id, { state });
  });

  return HttpResponse.json({ success: true });
});

// ============================================================================
// APP ENDPOINTS
// ============================================================================

/**
 * GET /api/v1/apps/ - Get apps
 */
const getApps = http.get('/api/v1/apps/', ({ request }) => {
  const url = new URL(request.url);
  const page = parseInt(url.searchParams.get('page') || '1');
  const page_size = parseInt(url.searchParams.get('page_size') || '10');

  // Generate mock apps
  const apps = Array.from({ length: 15 }, (_, index) => ({
    id: `app-${index + 1}`,
    name: `App ${index + 1}`,
    is_active: Math.random() > 0.3,
    memories: Math.floor(Math.random() * 100),
    memories_accessed: Math.floor(Math.random() * 50),
    created_at: new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000).toISOString(),
  }));

  const startIndex = (page - 1) * page_size;
  const endIndex = startIndex + page_size;
  const paginatedApps = apps.slice(startIndex, endIndex);

  return HttpResponse.json({
    total: apps.length,
    page,
    page_size,
    apps: paginatedApps,
  });
});

// ============================================================================
// CONFIG ENDPOINTS
// ============================================================================

/**
 * GET /api/v1/config - Get configuration
 */
const getConfig = http.get('/api/v1/config', () => {
  return HttpResponse.json({
    openmemory: {
      enabled: true,
      version: '1.0.0',
    },
    mem0: {
      enabled: false,
      api_key: null,
      base_url: 'https://api.mem0.ai',
    },
  });
});

/**
 * PUT /api/v1/config - Update configuration
 */
const updateConfig = http.put('/api/v1/config', async ({ request }) => {
  const body = await request.json() as any;
  
  return HttpResponse.json({
    ...body,
    updated_at: new Date().toISOString(),
  });
});

// Export all OpenMemory handlers
export const openMemoryHandlers = [
  filterMemories,
  createMemory,
  getMemory,
  updateMemory,
  deleteMemories,
  getMemoryAccessLogs,
  getRelatedMemories,
  updateMemoryState,
  getApps,
  getConfig,
  updateConfig,
];
