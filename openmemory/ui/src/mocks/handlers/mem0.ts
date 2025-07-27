// Mem0 API Mock Handlers
import { http, HttpResponse } from 'msw';
import {
  generateMem0Memory,
  generateMem0Memories,
  generateMem0Users,
  generateMem0MemoryHistory,
  mockDataStore,
} from '../data/generators';
import type { Memory as Mem0Memory, Message } from '@/lib/types/mem0';

// ============================================================================
// V1 API ENDPOINTS
// ============================================================================

/**
 * GET /v1/ping/ - Health check
 */
const pingV1 = http.get('/v1/ping/', () => {
  return HttpResponse.json({
    status: 'ok',
    message: 'Mem0 API is running',
    org_id: 'mock-org-123',
    project_id: 'mock-project-456',
    user_email: 'mock@example.com',
  });
});

/**
 * POST /v1/memories/ - Add memories
 */
const addMemoriesV1 = http.post('/v1/memories/', async ({ request }) => {
  const body = await request.json() as any;
  const { messages, user_id, agent_id, app_id, run_id, infer, custom_categories } = body;

  const newMemories = messages.map((message: Message) => {
    const memory = generateMem0Memory({
      memory: typeof message.content === 'string' ? message.content : JSON.stringify(message.content),
      messages: [message],
      user_id,
      agent_id,
      app_id,
      run_id,
      event: 'ADD',
    });
    
    mockDataStore.addMem0Memory(memory);
    return memory;
  });

  return HttpResponse.json(newMemories);
});

/**
 * GET /v1/memories/ - Get all memories
 */
const getMemoriesV1 = http.get('/v1/memories/', ({ request }) => {
  const url = new URL(request.url);
  const user_id = url.searchParams.get('user_id');
  const agent_id = url.searchParams.get('agent_id');
  const app_id = url.searchParams.get('app_id');
  const run_id = url.searchParams.get('run_id');
  const page = parseInt(url.searchParams.get('page') || '1');
  const page_size = parseInt(url.searchParams.get('page_size') || '10');

  let memories = mockDataStore.getMem0Memories();

  // Filter by parameters
  if (user_id) {
    memories = memories.filter(memory => memory.user_id === user_id);
  }
  if (agent_id) {
    memories = memories.filter(memory => memory.agent_id === agent_id);
  }
  if (app_id) {
    memories = memories.filter(memory => memory.app_id === app_id);
  }
  if (run_id) {
    memories = memories.filter(memory => memory.run_id === run_id);
  }

  // Paginate if requested
  if (page && page_size) {
    const startIndex = (page - 1) * page_size;
    const endIndex = startIndex + page_size;
    memories = memories.slice(startIndex, endIndex);
  }

  return HttpResponse.json(memories);
});

/**
 * GET /v1/memories/:id/ - Get specific memory
 */
const getMemoryV1 = http.get('/v1/memories/:id/', ({ params }) => {
  const { id } = params;
  const memory = mockDataStore.getMem0Memory(id as string);

  if (!memory) {
    return HttpResponse.json(
      { error: 'Memory not found' },
      { status: 404 }
    );
  }

  return HttpResponse.json(memory);
});

/**
 * PUT /v1/memories/:id/ - Update memory
 */
const updateMemoryV1 = http.put('/v1/memories/:id/', async ({ params, request }) => {
  const { id } = params;
  const body = await request.json() as any;
  const { text } = body;

  const updatedMemory = mockDataStore.updateMem0Memory(id as string, {
    memory: text,
    event: 'UPDATE',
    updated_at: new Date().toISOString(),
  });

  if (!updatedMemory) {
    return HttpResponse.json(
      { error: 'Memory not found' },
      { status: 404 }
    );
  }

  return HttpResponse.json([updatedMemory]);
});

/**
 * DELETE /v1/memories/:id/ - Delete memory
 */
const deleteMemoryV1 = http.delete('/v1/memories/:id/', ({ params }) => {
  const { id } = params;
  const deleted = mockDataStore.deleteMem0Memory(id as string);

  if (!deleted) {
    return HttpResponse.json(
      { error: 'Memory not found' },
      { status: 404 }
    );
  }

  return HttpResponse.json({ success: true });
});

/**
 * DELETE /v1/memories/ - Delete all memories for user
 */
const deleteAllMemoriesV1 = http.delete('/v1/memories/', async ({ request }) => {
  const body = await request.json() as any;
  const { user_id } = body;

  const memories = mockDataStore.getMem0Memories();
  const toDelete = memories.filter(memory => memory.user_id === user_id);
  
  toDelete.forEach(memory => {
    mockDataStore.deleteMem0Memory(memory.id);
  });

  return HttpResponse.json({ success: true, deleted_count: toDelete.length });
});

/**
 * GET /v1/memories/:id/history/ - Get memory history
 */
const getMemoryHistoryV1 = http.get('/v1/memories/:id/history/', ({ params }) => {
  const { id } = params;
  
  // Generate mock history
  const history = Array.from({ length: 5 }, () => 
    generateMem0MemoryHistory(id as string)
  );

  return HttpResponse.json(history);
});

// ============================================================================
// V2 API ENDPOINTS
// ============================================================================

/**
 * POST /v2/memories/ - Add memories (v2)
 */
const addMemoriesV2 = http.post('/v2/memories/', async ({ request }) => {
  const body = await request.json() as any;
  
  // V2 API has different structure
  const newMemories = generateMem0Memories(1);
  newMemories.forEach(memory => {
    mockDataStore.addMem0Memory(memory);
  });

  return HttpResponse.json(newMemories);
});

/**
 * POST /v2/memories/ - Get memories with search (v2)
 */
const getMemoriesV2 = http.post('/v2/memories/', async ({ request }) => {
  const body = await request.json() as any;
  const { user_id, agent_id, app_id, limit = 10, threshold, keyword_search, rerank } = body;

  let memories = mockDataStore.getMem0Memories();

  // Filter by parameters
  if (user_id) {
    memories = memories.filter(memory => memory.user_id === user_id);
  }
  if (agent_id) {
    memories = memories.filter(memory => memory.agent_id === agent_id);
  }
  if (app_id) {
    memories = memories.filter(memory => memory.app_id === app_id);
  }

  // Apply limit
  memories = memories.slice(0, limit);

  // Add scores for search results
  const memoriesWithScores = memories.map(memory => ({
    ...memory,
    score: Math.random() * (threshold || 1),
  }));

  return HttpResponse.json(memoriesWithScores);
});

// ============================================================================
// BATCH OPERATIONS
// ============================================================================

/**
 * PUT /v1/memories/batch/ - Batch update memories
 */
const batchUpdateMemories = http.put('/v1/memories/batch/', async ({ request }) => {
  const body = await request.json() as any;
  const { updates } = body;

  const updatedMemories = updates.map((update: any) => {
    const { memory_id, text } = update;
    return mockDataStore.updateMem0Memory(memory_id, {
      memory: text,
      event: 'UPDATE',
      updated_at: new Date().toISOString(),
    });
  }).filter(Boolean);

  return HttpResponse.json(updatedMemories);
});

/**
 * DELETE /v1/memories/batch/ - Batch delete memories
 */
const batchDeleteMemories = http.delete('/v1/memories/batch/', async ({ request }) => {
  const body = await request.json() as any;
  const { memory_ids } = body;

  memory_ids.forEach((id: string) => {
    mockDataStore.deleteMem0Memory(id);
  });

  return HttpResponse.json({ success: true, deleted_count: memory_ids.length });
});

// ============================================================================
// USER MANAGEMENT
// ============================================================================

/**
 * GET /v1/users/ - Get all users
 */
const getUsersV1 = http.get('/v1/users/', () => {
  const users = mockDataStore.getUsers();
  
  return HttpResponse.json({
    count: users.length,
    results: users,
    next: null,
    previous: null,
  });
});

/**
 * DELETE /v1/users/ - Delete users
 */
const deleteUsersV1 = http.delete('/v1/users/', async ({ request }) => {
  const body = await request.json() as any;
  const { user_ids } = body;

  // In a real implementation, this would delete users and their memories
  return HttpResponse.json({ success: true, deleted_count: user_ids.length });
});

// ============================================================================
// ERROR SIMULATION
// ============================================================================

/**
 * Simulate network errors for testing
 */
const simulateError = http.get('/v1/simulate-error/:type', ({ params }) => {
  const { type } = params;
  
  switch (type) {
    case '500':
      return HttpResponse.json(
        { error: 'Internal server error' },
        { status: 500 }
      );
    case '429':
      return HttpResponse.json(
        { error: 'Rate limit exceeded' },
        { status: 429 }
      );
    case '401':
      return HttpResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    default:
      return HttpResponse.json(
        { error: 'Bad request' },
        { status: 400 }
      );
  }
});

// Export all Mem0 handlers
export const mem0Handlers = [
  // V1 API
  pingV1,
  addMemoriesV1,
  getMemoriesV1,
  getMemoryV1,
  updateMemoryV1,
  deleteMemoryV1,
  deleteAllMemoriesV1,
  getMemoryHistoryV1,
  
  // V2 API
  addMemoriesV2,
  getMemoriesV2,
  
  // Batch operations
  batchUpdateMemories,
  batchDeleteMemories,
  
  // User management
  getUsersV1,
  deleteUsersV1,
  
  // Error simulation
  simulateError,
];
