// Mock data generators for API responses
import type { Memory as OpenMemoryMemory, Category, Client } from '@/components/types';
import type { Memory as Mem0Memory, Message, User, MemoryHistory } from '@/lib/types/mem0';

// Sample data arrays
const SAMPLE_CATEGORIES: Category[] = ['personal', 'work', 'health', 'finance', 'travel', 'education', 'preferences', 'relationships'];
const SAMPLE_CLIENTS: Client[] = ['chrome', 'chatgpt', 'cursor', 'windsurf', 'terminal', 'api'];
const SAMPLE_APP_NAMES = ['openmemory', 'chrome-extension', 'chatgpt-plugin', 'cursor-extension', 'terminal-app'];
const SAMPLE_USER_IDS = ['user-001', 'user-002', 'user-003', 'user-004', 'user-005'];
const SAMPLE_AGENT_IDS = ['agent-001', 'agent-002', 'agent-003'];

const SAMPLE_MEMORY_CONTENTS = [
  'I prefer dark mode in all applications',
  'My favorite programming language is TypeScript',
  'I work remotely from San Francisco',
  'I have a meeting with the design team every Tuesday at 2 PM',
  'My preferred coffee is Ethiopian single origin',
  'I use VS Code as my primary editor',
  'I follow a Mediterranean diet',
  'My workout schedule is Monday, Wednesday, Friday at 7 AM',
  'I prefer async communication over meetings',
  'My timezone is PST/PDT',
];

// Utility functions
function randomChoice<T>(array: T[]): T {
  return array[Math.floor(Math.random() * array.length)];
}

function randomChoices<T>(array: T[], count: number = 1): T[] {
  const shuffled = [...array].sort(() => 0.5 - Math.random());
  return shuffled.slice(0, Math.min(count, array.length));
}

function randomId(prefix: string = 'id'): string {
  return `${prefix}-${Math.random().toString(36).substr(2, 9)}`;
}

function randomDate(start: Date = new Date(2023, 0, 1), end: Date = new Date()): Date {
  return new Date(start.getTime() + Math.random() * (end.getTime() - start.getTime()));
}

// ============================================================================
// OPENMEMORY MOCK DATA GENERATORS
// ============================================================================

/**
 * Generate a single OpenMemory memory
 */
export function generateOpenMemoryMemory(overrides: Partial<OpenMemoryMemory> = {}): OpenMemoryMemory {
  const baseMemory: OpenMemoryMemory = {
    id: randomId('mem'),
    memory: randomChoice(SAMPLE_MEMORY_CONTENTS),
    metadata: {
      source: 'mock',
      generated_at: new Date().toISOString(),
      confidence: Math.random(),
    },
    client: randomChoice(SAMPLE_CLIENTS),
    categories: randomChoices(SAMPLE_CATEGORIES, Math.floor(Math.random() * 3) + 1),
    created_at: randomDate().getTime(),
    app_name: randomChoice(SAMPLE_APP_NAMES),
    state: randomChoice(['active', 'paused', 'archived', 'deleted']),
  };

  return { ...baseMemory, ...overrides };
}

/**
 * Generate multiple OpenMemory memories
 */
export function generateOpenMemoryMemories(count: number = 10): OpenMemoryMemory[] {
  return Array.from({ length: count }, () => generateOpenMemoryMemory());
}

/**
 * Generate OpenMemory API response format
 */
export function generateOpenMemoryApiResponse(count: number = 10, page: number = 1, pageSize: number = 10) {
  const memories = generateOpenMemoryMemories(count);
  return {
    items: memories,
    total: count,
    page,
    size: pageSize,
    pages: Math.ceil(count / pageSize),
  };
}

/**
 * Generate OpenMemory simple memory format
 */
export function generateOpenMemorySimpleMemory(overrides: any = {}) {
  const memory = generateOpenMemoryMemory();
  return {
    id: memory.id,
    text: memory.memory,
    created_at: new Date(memory.created_at).toISOString(),
    state: memory.state,
    categories: memory.categories,
    app_name: memory.app_name,
    ...overrides,
  };
}

// ============================================================================
// MEM0 MOCK DATA GENERATORS
// ============================================================================

/**
 * Generate a Mem0 message
 */
export function generateMem0Message(overrides: Partial<Message> = {}): Message {
  const baseMessage: Message = {
    role: randomChoice(['user', 'assistant', 'system']),
    content: randomChoice(SAMPLE_MEMORY_CONTENTS),
  };

  return { ...baseMessage, ...overrides };
}

/**
 * Generate multiple Mem0 messages
 */
export function generateMem0Messages(count: number = 1): Message[] {
  return Array.from({ length: count }, () => generateMem0Message());
}

/**
 * Generate a single Mem0 memory
 */
export function generateMem0Memory(overrides: Partial<Mem0Memory> = {}): Mem0Memory {
  const baseMemory: Mem0Memory = {
    id: randomId('mem0'),
    memory: randomChoice(SAMPLE_MEMORY_CONTENTS),
    messages: generateMem0Messages(Math.floor(Math.random() * 3) + 1),
    event: randomChoice(['ADD', 'UPDATE', 'DELETE', 'NOOP']),
    created_at: randomDate().toISOString(),
    updated_at: randomDate().toISOString(),
    categories: randomChoices(SAMPLE_CATEGORIES, Math.floor(Math.random() * 3) + 1),
    metadata: {
      source: 'mock',
      generated_at: new Date().toISOString(),
      confidence: Math.random(),
    },
    user_id: randomChoice(SAMPLE_USER_IDS),
    agent_id: randomChoice(SAMPLE_AGENT_IDS),
    app_id: randomId('app'),
    run_id: randomId('run'),
    hash: randomId('hash'),
    memory_type: randomChoice(['episodic', 'semantic', 'procedural']),
    score: Math.random(),
    owner: randomChoice(SAMPLE_USER_IDS),
  };

  return { ...baseMemory, ...overrides };
}

/**
 * Generate multiple Mem0 memories
 */
export function generateMem0Memories(count: number = 10): Mem0Memory[] {
  return Array.from({ length: count }, () => generateMem0Memory());
}

/**
 * Generate Mem0 user
 */
export function generateMem0User(overrides: Partial<User> = {}): User {
  const baseUser: User = {
    id: randomChoice(SAMPLE_USER_IDS),
    name: `User ${Math.floor(Math.random() * 1000)}`,
    created_at: randomDate().toISOString(),
    updated_at: randomDate().toISOString(),
    total_memories: Math.floor(Math.random() * 100),
    owner: randomChoice(SAMPLE_USER_IDS),
    type: randomChoice(['individual', 'organization', 'bot']),
  };

  return { ...baseUser, ...overrides };
}

/**
 * Generate multiple Mem0 users
 */
export function generateMem0Users(count: number = 5): User[] {
  return Array.from({ length: count }, () => generateMem0User());
}

/**
 * Generate Mem0 memory history
 */
export function generateMem0MemoryHistory(memoryId: string, overrides: Partial<MemoryHistory> = {}): MemoryHistory {
  const baseHistory: MemoryHistory = {
    id: randomId('hist'),
    memory_id: memoryId,
    input: generateMem0Messages(1),
    old_memory: randomChoice([null, randomChoice(SAMPLE_MEMORY_CONTENTS)]),
    new_memory: randomChoice(SAMPLE_MEMORY_CONTENTS),
    user_id: randomChoice(SAMPLE_USER_IDS),
    categories: randomChoices(SAMPLE_CATEGORIES, Math.floor(Math.random() * 2) + 1),
    event: randomChoice(['ADD', 'UPDATE', 'DELETE']),
    created_at: randomDate().toISOString(),
    updated_at: randomDate().toISOString(),
  };

  return { ...baseHistory, ...overrides };
}

// ============================================================================
// DYNAMIC DATA MANAGEMENT
// ============================================================================

/**
 * In-memory data store for dynamic mock data
 */
export class MockDataStore {
  private openMemoryMemories: Map<string, OpenMemoryMemory> = new Map();
  private mem0Memories: Map<string, Mem0Memory> = new Map();
  private users: Map<string, User> = new Map();

  constructor() {
    this.initializeData();
  }

  private initializeData() {
    // Initialize with some default data
    const openMemories = generateOpenMemoryMemories(20);
    openMemories.forEach(memory => {
      this.openMemoryMemories.set(memory.id, memory);
    });

    const mem0Memories = generateMem0Memories(20);
    mem0Memories.forEach(memory => {
      this.mem0Memories.set(memory.id, memory);
    });

    const users = generateMem0Users(10);
    users.forEach(user => {
      this.users.set(user.id, user);
    });
  }

  // OpenMemory operations
  getOpenMemoryMemories(): OpenMemoryMemory[] {
    return Array.from(this.openMemoryMemories.values());
  }

  getOpenMemoryMemory(id: string): OpenMemoryMemory | undefined {
    return this.openMemoryMemories.get(id);
  }

  addOpenMemoryMemory(memory: OpenMemoryMemory): void {
    this.openMemoryMemories.set(memory.id, memory);
  }

  updateOpenMemoryMemory(id: string, updates: Partial<OpenMemoryMemory>): OpenMemoryMemory | undefined {
    const existing = this.openMemoryMemories.get(id);
    if (existing) {
      const updated = { ...existing, ...updates };
      this.openMemoryMemories.set(id, updated);
      return updated;
    }
    return undefined;
  }

  deleteOpenMemoryMemory(id: string): boolean {
    return this.openMemoryMemories.delete(id);
  }

  // Mem0 operations
  getMem0Memories(): Mem0Memory[] {
    return Array.from(this.mem0Memories.values());
  }

  getMem0Memory(id: string): Mem0Memory | undefined {
    return this.mem0Memories.get(id);
  }

  addMem0Memory(memory: Mem0Memory): void {
    this.mem0Memories.set(memory.id, memory);
  }

  updateMem0Memory(id: string, updates: Partial<Mem0Memory>): Mem0Memory | undefined {
    const existing = this.mem0Memories.get(id);
    if (existing) {
      const updated = { ...existing, ...updates };
      this.mem0Memories.set(id, updated);
      return updated;
    }
    return undefined;
  }

  deleteMem0Memory(id: string): boolean {
    return this.mem0Memories.delete(id);
  }

  // User operations
  getUsers(): User[] {
    return Array.from(this.users.values());
  }

  getUser(id: string): User | undefined {
    return this.users.get(id);
  }

  // Reset data
  reset(): void {
    this.openMemoryMemories.clear();
    this.mem0Memories.clear();
    this.users.clear();
    this.initializeData();
  }
}

// Export singleton instance
export const mockDataStore = new MockDataStore();
