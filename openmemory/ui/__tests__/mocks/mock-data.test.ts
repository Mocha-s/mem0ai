// Mock Data Generators Unit Tests
import {
  generateOpenMemoryMemory,
  generateOpenMemoryMemories,
  generateMem0Memory,
  generateMem0Memories,
  generateMem0User,
  generateMem0Message,
  MockDataStore,
  mockDataStore,
} from '@/src/mocks/data/generators';
import type { Memory as OpenMemoryMemory } from '@/components/types';
import type { Memory as Mem0Memory, User, Message } from '@/lib/types/mem0';

describe('Mock Data Generators', () => {
  describe('OpenMemory Data Generation', () => {
    it('should generate valid OpenMemory memory', () => {
      const memory = generateOpenMemoryMemory();

      expect(memory).toHaveProperty('id');
      expect(memory).toHaveProperty('memory');
      expect(memory).toHaveProperty('metadata');
      expect(memory).toHaveProperty('client');
      expect(memory).toHaveProperty('categories');
      expect(memory).toHaveProperty('created_at');
      expect(memory).toHaveProperty('app_name');
      expect(memory).toHaveProperty('state');

      expect(typeof memory.id).toBe('string');
      expect(typeof memory.memory).toBe('string');
      expect(typeof memory.created_at).toBe('number');
      expect(Array.isArray(memory.categories)).toBe(true);
      expect(['active', 'paused', 'archived', 'deleted']).toContain(memory.state);
    });

    it('should generate OpenMemory memory with overrides', () => {
      const overrides: Partial<OpenMemoryMemory> = {
        memory: 'Custom memory content',
        state: 'active',
        client: 'api',
      };

      const memory = generateOpenMemoryMemory(overrides);

      expect(memory.memory).toBe('Custom memory content');
      expect(memory.state).toBe('active');
      expect(memory.client).toBe('api');
    });

    it('should generate multiple OpenMemory memories', () => {
      const count = 5;
      const memories = generateOpenMemoryMemories(count);

      expect(memories).toHaveLength(count);
      expect(memories.every(m => typeof m.id === 'string')).toBe(true);
      expect(memories.every(m => typeof m.memory === 'string')).toBe(true);

      // Check that IDs are unique
      const ids = memories.map(m => m.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(count);
    });

    it('should generate valid metadata structure', () => {
      const memory = generateOpenMemoryMemory();

      expect(memory.metadata).toHaveProperty('source', 'mock');
      expect(memory.metadata).toHaveProperty('generated_at');
      expect(memory.metadata).toHaveProperty('confidence');
      expect(typeof memory.metadata.confidence).toBe('number');
      expect(memory.metadata.confidence).toBeGreaterThanOrEqual(0);
      expect(memory.metadata.confidence).toBeLessThanOrEqual(1);
    });
  });

  describe('Mem0 Data Generation', () => {
    it('should generate valid Mem0 memory', () => {
      const memory = generateMem0Memory();

      expect(memory).toHaveProperty('id');
      expect(memory).toHaveProperty('memory');
      expect(memory).toHaveProperty('messages');
      expect(memory).toHaveProperty('event');
      expect(memory).toHaveProperty('created_at');
      expect(memory).toHaveProperty('categories');
      expect(memory).toHaveProperty('user_id');

      expect(typeof memory.id).toBe('string');
      expect(typeof memory.memory).toBe('string');
      expect(Array.isArray(memory.messages)).toBe(true);
      expect(Array.isArray(memory.categories)).toBe(true);
      expect(['ADD', 'UPDATE', 'DELETE', 'NOOP']).toContain(memory.event);
    });

    it('should generate Mem0 memory with overrides', () => {
      const overrides: Partial<Mem0Memory> = {
        memory: 'Custom Mem0 content',
        user_id: 'custom-user-123',
        event: 'UPDATE',
      };

      const memory = generateMem0Memory(overrides);

      expect(memory.memory).toBe('Custom Mem0 content');
      expect(memory.user_id).toBe('custom-user-123');
      expect(memory.event).toBe('UPDATE');
    });

    it('should generate multiple Mem0 memories', () => {
      const count = 3;
      const memories = generateMem0Memories(count);

      expect(memories).toHaveLength(count);
      expect(memories.every(m => typeof m.id === 'string')).toBe(true);
      expect(memories.every(m => typeof m.memory === 'string')).toBe(true);

      // Check that IDs are unique
      const ids = memories.map(m => m.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(count);
    });

    it('should generate valid messages array', () => {
      const memory = generateMem0Memory();

      expect(memory.messages).toBeDefined();
      expect(Array.isArray(memory.messages)).toBe(true);
      expect(memory.messages!.length).toBeGreaterThan(0);
      expect(memory.messages!.length).toBeLessThanOrEqual(4);

      memory.messages!.forEach(message => {
        expect(message).toHaveProperty('role');
        expect(message).toHaveProperty('content');
        expect(['user', 'assistant', 'system']).toContain(message.role);
        expect(typeof message.content).toBe('string');
      });
    });
  });

  describe('Mem0 User Generation', () => {
    it('should generate valid Mem0 user', () => {
      const user = generateMem0User();

      expect(user).toHaveProperty('id');
      expect(user).toHaveProperty('name');
      expect(user).toHaveProperty('created_at');
      expect(user).toHaveProperty('updated_at');
      expect(user).toHaveProperty('total_memories');
      expect(user).toHaveProperty('owner');
      expect(user).toHaveProperty('type');

      expect(typeof user.id).toBe('string');
      expect(typeof user.name).toBe('string');
      expect(typeof user.total_memories).toBe('number');
      expect(['individual', 'organization', 'bot']).toContain(user.type);
    });

    it('should generate user with overrides', () => {
      const overrides: Partial<User> = {
        name: 'Custom User',
        type: 'organization',
        total_memories: 100,
      };

      const user = generateMem0User(overrides);

      expect(user.name).toBe('Custom User');
      expect(user.type).toBe('organization');
      expect(user.total_memories).toBe(100);
    });
  });

  describe('Mem0 Message Generation', () => {
    it('should generate valid Mem0 message', () => {
      const message = generateMem0Message();

      expect(message).toHaveProperty('role');
      expect(message).toHaveProperty('content');
      expect(['user', 'assistant', 'system']).toContain(message.role);
      expect(typeof message.content).toBe('string');
    });

    it('should generate message with overrides', () => {
      const overrides: Partial<Message> = {
        role: 'assistant',
        content: 'Custom message content',
      };

      const message = generateMem0Message(overrides);

      expect(message.role).toBe('assistant');
      expect(message.content).toBe('Custom message content');
    });
  });

  describe('MockDataStore', () => {
    let dataStore: MockDataStore;

    beforeEach(() => {
      dataStore = new MockDataStore();
    });

    describe('OpenMemory Operations', () => {
      it('should initialize with default data', () => {
        const memories = dataStore.getOpenMemoryMemories();
        expect(memories.length).toBeGreaterThan(0);
      });

      it('should add OpenMemory memory', () => {
        const initialCount = dataStore.getOpenMemoryMemories().length;
        const newMemory = generateOpenMemoryMemory({ id: 'test-add' });

        dataStore.addOpenMemoryMemory(newMemory);

        const memories = dataStore.getOpenMemoryMemories();
        expect(memories.length).toBe(initialCount + 1);
        expect(dataStore.getOpenMemoryMemory('test-add')).toEqual(newMemory);
      });

      it('should update OpenMemory memory', () => {
        const memory = generateOpenMemoryMemory({ id: 'test-update' });
        dataStore.addOpenMemoryMemory(memory);

        const updates = { memory: 'Updated content' };
        const updated = dataStore.updateOpenMemoryMemory('test-update', updates);

        expect(updated).toBeDefined();
        expect(updated!.memory).toBe('Updated content');
        expect(updated!.id).toBe('test-update');
      });

      it('should delete OpenMemory memory', () => {
        const memory = generateOpenMemoryMemory({ id: 'test-delete' });
        dataStore.addOpenMemoryMemory(memory);

        const deleted = dataStore.deleteOpenMemoryMemory('test-delete');
        expect(deleted).toBe(true);
        expect(dataStore.getOpenMemoryMemory('test-delete')).toBeUndefined();
      });

      it('should handle non-existent memory operations', () => {
        expect(dataStore.getOpenMemoryMemory('non-existent')).toBeUndefined();
        expect(dataStore.updateOpenMemoryMemory('non-existent', {})).toBeUndefined();
        expect(dataStore.deleteOpenMemoryMemory('non-existent')).toBe(false);
      });
    });

    describe('Mem0 Operations', () => {
      it('should initialize with default data', () => {
        const memories = dataStore.getMem0Memories();
        expect(memories.length).toBeGreaterThan(0);
      });

      it('should add Mem0 memory', () => {
        const initialCount = dataStore.getMem0Memories().length;
        const newMemory = generateMem0Memory({ id: 'test-add-mem0' });

        dataStore.addMem0Memory(newMemory);

        const memories = dataStore.getMem0Memories();
        expect(memories.length).toBe(initialCount + 1);
        expect(dataStore.getMem0Memory('test-add-mem0')).toEqual(newMemory);
      });

      it('should update Mem0 memory', () => {
        const memory = generateMem0Memory({ id: 'test-update-mem0' });
        dataStore.addMem0Memory(memory);

        const updates = { memory: 'Updated Mem0 content' };
        const updated = dataStore.updateMem0Memory('test-update-mem0', updates);

        expect(updated).toBeDefined();
        expect(updated!.memory).toBe('Updated Mem0 content');
        expect(updated!.id).toBe('test-update-mem0');
      });

      it('should delete Mem0 memory', () => {
        const memory = generateMem0Memory({ id: 'test-delete-mem0' });
        dataStore.addMem0Memory(memory);

        const deleted = dataStore.deleteMem0Memory('test-delete-mem0');
        expect(deleted).toBe(true);
        expect(dataStore.getMem0Memory('test-delete-mem0')).toBeUndefined();
      });
    });

    describe('User Operations', () => {
      it('should initialize with default users', () => {
        const users = dataStore.getUsers();
        expect(users.length).toBeGreaterThan(0);
      });

      it('should get user by ID', () => {
        const users = dataStore.getUsers();
        const firstUser = users[0];
        const retrieved = dataStore.getUser(firstUser.id);

        expect(retrieved).toEqual(firstUser);
      });

      it('should handle non-existent user', () => {
        expect(dataStore.getUser('non-existent-user')).toBeUndefined();
      });
    });

    describe('Data Reset', () => {
      it('should reset all data', () => {
        // Add some custom data
        dataStore.addOpenMemoryMemory(generateOpenMemoryMemory({ id: 'custom' }));
        dataStore.addMem0Memory(generateMem0Memory({ id: 'custom-mem0' }));

        // Reset
        dataStore.reset();

        // Should have fresh data but not the custom ones
        expect(dataStore.getOpenMemoryMemory('custom')).toBeUndefined();
        expect(dataStore.getMem0Memory('custom-mem0')).toBeUndefined();
        expect(dataStore.getOpenMemoryMemories().length).toBeGreaterThan(0);
        expect(dataStore.getMem0Memories().length).toBeGreaterThan(0);
      });
    });
  });

  describe('Global Mock Data Store', () => {
    it('should provide singleton instance', () => {
      expect(mockDataStore).toBeInstanceOf(MockDataStore);
      expect(mockDataStore.getOpenMemoryMemories().length).toBeGreaterThan(0);
      expect(mockDataStore.getMem0Memories().length).toBeGreaterThan(0);
      expect(mockDataStore.getUsers().length).toBeGreaterThan(0);
    });
  });
});
