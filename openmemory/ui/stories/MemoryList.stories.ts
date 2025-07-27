import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { MemoryList } from '@/components/mem0/MemoryList';
import type { UnifiedMemory } from '@/lib/types/unified';

// Generate mock memories
const generateMockMemories = (count: number): UnifiedMemory[] => {
  const categories = ['personal', 'work', 'health', 'finance', 'travel', 'education'];
  const clients = ['chrome', 'chatgpt', 'cursor', 'terminal', 'api'];
  const states = ['active', 'paused', 'archived'] as const;
  
  return Array.from({ length: count }, (_, i) => ({
    id: `memory-${i + 1}`,
    content: `Sample memory content ${i + 1}. This demonstrates different memory entries with varying content lengths and metadata. ${i % 3 === 0 ? 'This is a longer description that shows how the component handles extended text content and wrapping behavior.' : ''}`,
    created_at: new Date(Date.now() - (i * 24 * 60 * 60 * 1000)).toISOString(),
    updated_at: new Date(Date.now() - (i * 12 * 60 * 60 * 1000)).toISOString(),
    categories: categories.slice(0, (i % 3) + 1),
    metadata: { 
      source: 'test', 
      confidence: 0.8 + (i % 3) * 0.1,
      index: i 
    },
    client: clients[i % clients.length],
    app_name: 'openmemory',
    state: states[i % states.length],
    user_id: `user-${(i % 3) + 1}`,
    score: 0.7 + (i % 4) * 0.1,
    agent_id: `agent-${(i % 2) + 1}`,
    memory_type: i % 2 === 0 ? 'episodic' : 'semantic',
  }));
};

const mockMemories = generateMockMemories(15);
const fewMemories = generateMockMemories(3);
const manyMemories = generateMockMemories(50);

const meta: Meta<typeof MemoryList> = {
  title: 'Mem0/MemoryList',
  component: MemoryList,
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: 'A list component for displaying multiple memory items with sorting, pagination, and batch operations.',
      },
    },
  },
  tags: ['autodocs'],
  argTypes: {
    memories: {
      description: 'Array of memory objects to display',
      control: { type: 'object' },
    },
    loading: {
      description: 'Whether the list is in loading state',
      control: { type: 'boolean' },
    },
    error: {
      description: 'Error message to display',
      control: { type: 'text' },
    },
    onEdit: {
      description: 'Callback function when edit action is triggered',
      action: 'edit',
    },
    onDelete: {
      description: 'Callback function when delete action is triggered',
      action: 'delete',
    },
    onBatchDelete: {
      description: 'Callback function when batch delete is triggered',
      action: 'batchDelete',
    },
    onView: {
      description: 'Callback function when view action is triggered',
      action: 'view',
    },
    onRefresh: {
      description: 'Callback function when refresh is triggered',
      action: 'refresh',
    },
    showBatchActions: {
      description: 'Whether to show batch action controls',
      control: { type: 'boolean' },
    },
    defaultViewMode: {
      description: 'Default view mode',
      control: { type: 'select' },
      options: ['grid', 'list'],
    },
    defaultSortBy: {
      description: 'Default sort field',
      control: { type: 'select' },
      options: ['created_at', 'updated_at', 'content', 'score'],
    },
    defaultSortOrder: {
      description: 'Default sort order',
      control: { type: 'select' },
      options: ['asc', 'desc'],
    },
    itemsPerPage: {
      description: 'Number of items per page',
      control: { type: 'number', min: 5, max: 50, step: 5 },
    },
    emptyMessage: {
      description: 'Message to show when no memories are found',
      control: { type: 'text' },
    },
  },
  args: {
    onEdit: fn(),
    onDelete: fn(),
    onBatchDelete: fn(),
    onView: fn(),
    onRefresh: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default memory list with standard configuration
 */
export const Default: Story = {
  args: {
    memories: mockMemories,
    loading: false,
    error: null,
    showBatchActions: true,
    defaultViewMode: 'grid',
    defaultSortBy: 'created_at',
    defaultSortOrder: 'desc',
    itemsPerPage: 10,
  },
};

/**
 * List view mode
 */
export const ListView: Story = {
  args: {
    ...Default.args,
    defaultViewMode: 'list',
  },
};

/**
 * Loading state
 */
export const Loading: Story = {
  args: {
    memories: [],
    loading: true,
    error: null,
    showBatchActions: true,
  },
};

/**
 * Error state
 */
export const Error: Story = {
  args: {
    memories: [],
    loading: false,
    error: 'Failed to load memories. Please try again.',
    showBatchActions: true,
  },
};

/**
 * Empty state
 */
export const Empty: Story = {
  args: {
    memories: [],
    loading: false,
    error: null,
    showBatchActions: true,
    emptyMessage: 'No memories found. Create your first memory to get started.',
  },
};

/**
 * Few memories (no pagination)
 */
export const FewMemories: Story = {
  args: {
    memories: fewMemories,
    loading: false,
    error: null,
    showBatchActions: true,
    itemsPerPage: 10,
  },
};

/**
 * Many memories (with pagination)
 */
export const ManyMemories: Story = {
  args: {
    memories: manyMemories,
    loading: false,
    error: null,
    showBatchActions: true,
    itemsPerPage: 8,
  },
};

/**
 * Without batch actions
 */
export const NoBatchActions: Story = {
  args: {
    ...Default.args,
    showBatchActions: false,
  },
};

/**
 * Small page size
 */
export const SmallPageSize: Story = {
  args: {
    ...Default.args,
    itemsPerPage: 5,
  },
};

/**
 * Sorted by score
 */
export const SortedByScore: Story = {
  args: {
    ...Default.args,
    defaultSortBy: 'score',
    defaultSortOrder: 'desc',
  },
};

/**
 * Sorted by content
 */
export const SortedByContent: Story = {
  args: {
    ...Default.args,
    defaultSortBy: 'content',
    defaultSortOrder: 'asc',
  },
};

/**
 * Interactive example with working actions
 */
export const Interactive: Story = {
  render: (args) => {
    const handleEdit = (id: string) => {
      console.log('Edit memory:', id);
      args.onEdit?.(id);
    };

    const handleDelete = (id: string) => {
      console.log('Delete memory:', id);
      args.onDelete?.(id);
    };

    const handleBatchDelete = (ids: string[]) => {
      console.log('Batch delete memories:', ids);
      args.onBatchDelete?.(ids);
    };

    const handleView = (id: string) => {
      console.log('View memory:', id);
      args.onView?.(id);
    };

    const handleRefresh = () => {
      console.log('Refresh memories');
      args.onRefresh?.();
    };

    return (
      <div className="p-4">
        <MemoryList
          {...args}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onBatchDelete={handleBatchDelete}
          onView={handleView}
          onRefresh={handleRefresh}
        />
        <div className="mt-4 text-sm text-muted-foreground">
          <p>Try interacting with the memories. Check the console for action events.</p>
        </div>
      </div>
    );
  },
  args: {
    memories: mockMemories,
    loading: false,
    error: null,
    showBatchActions: true,
    itemsPerPage: 6,
  },
  parameters: {
    layout: 'fullscreen',
  },
};

/**
 * Different view modes comparison
 */
export const ViewModeComparison: Story = {
  render: () => (
    <div className="space-y-8 p-4">
      <div>
        <h3 className="text-lg font-semibold mb-4">Grid View</h3>
        <MemoryList
          memories={fewMemories}
          defaultViewMode="grid"
          showBatchActions={false}
          itemsPerPage={10}
          onEdit={fn()}
          onDelete={fn()}
        />
      </div>
      <div>
        <h3 className="text-lg font-semibold mb-4">List View</h3>
        <MemoryList
          memories={fewMemories}
          defaultViewMode="list"
          showBatchActions={false}
          itemsPerPage={10}
          onEdit={fn()}
          onDelete={fn()}
        />
      </div>
    </div>
  ),
  parameters: {
    layout: 'fullscreen',
  },
};
