import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { MemoryCard } from '@/components/mem0/MemoryCard';
import type { UnifiedMemory } from '@/lib/types/unified';

// Mock memory data
const mockMemory: UnifiedMemory = {
  id: 'memory-1',
  content: 'This is a sample memory content that demonstrates how the MemoryCard component displays memory information with various metadata and actions. It includes categories, timestamps, and user information.',
  created_at: '2024-01-15T10:30:00Z',
  updated_at: '2024-01-15T11:00:00Z',
  categories: ['personal', 'work', 'important'],
  metadata: { 
    source: 'test', 
    confidence: 0.95,
    tags: ['demo', 'example']
  },
  client: 'chrome',
  app_name: 'openmemory',
  state: 'active',
  user_id: 'user-123',
  score: 0.87,
  agent_id: 'agent-456',
  memory_type: 'episodic',
};

const longContentMemory: UnifiedMemory = {
  ...mockMemory,
  id: 'memory-long',
  content: 'This is a much longer memory content that demonstrates how the MemoryCard component handles extensive text. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.',
  categories: ['personal', 'work', 'important', 'research', 'documentation'],
};

const minimalMemory: UnifiedMemory = {
  id: 'memory-minimal',
  content: 'Minimal memory with basic information.',
  created_at: '2024-01-15T10:30:00Z',
};

const meta: Meta<typeof MemoryCard> = {
  title: 'Mem0/MemoryCard',
  component: MemoryCard,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: 'A card component for displaying memory items with metadata, actions, and various display modes.',
      },
    },
  },
  tags: ['autodocs'],
  argTypes: {
    memory: {
      description: 'The memory object to display',
      control: { type: 'object' },
    },
    onEdit: {
      description: 'Callback function when edit action is triggered',
      action: 'edit',
    },
    onDelete: {
      description: 'Callback function when delete action is triggered',
      action: 'delete',
    },
    onView: {
      description: 'Callback function when view action is triggered',
      action: 'view',
    },
    compact: {
      description: 'Whether to display the card in compact mode',
      control: { type: 'boolean' },
    },
    showActions: {
      description: 'Whether to show action buttons',
      control: { type: 'boolean' },
    },
    showMetadata: {
      description: 'Whether to show metadata information',
      control: { type: 'boolean' },
    },
    className: {
      description: 'Additional CSS classes',
      control: { type: 'text' },
    },
  },
  args: {
    onEdit: fn(),
    onDelete: fn(),
    onView: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default memory card with all features enabled
 */
export const Default: Story = {
  args: {
    memory: mockMemory,
    showActions: true,
    showMetadata: true,
    compact: false,
  },
};

/**
 * Compact mode for displaying memory cards in lists
 */
export const Compact: Story = {
  args: {
    memory: mockMemory,
    compact: true,
    showActions: true,
    showMetadata: false,
  },
};

/**
 * Memory card with long content to test text truncation
 */
export const LongContent: Story = {
  args: {
    memory: longContentMemory,
    showActions: true,
    showMetadata: true,
    compact: false,
  },
};

/**
 * Compact mode with long content
 */
export const CompactLongContent: Story = {
  args: {
    memory: longContentMemory,
    compact: true,
    showActions: true,
    showMetadata: false,
  },
};

/**
 * Minimal memory with basic information only
 */
export const Minimal: Story = {
  args: {
    memory: minimalMemory,
    showActions: true,
    showMetadata: true,
    compact: false,
  },
};

/**
 * Memory card without actions
 */
export const NoActions: Story = {
  args: {
    memory: mockMemory,
    showActions: false,
    showMetadata: true,
    compact: false,
  },
};

/**
 * Memory card without metadata
 */
export const NoMetadata: Story = {
  args: {
    memory: mockMemory,
    showActions: true,
    showMetadata: false,
    compact: false,
  },
};

/**
 * Memory card with different states
 */
export const DifferentStates: Story = {
  render: () => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-4xl">
      <MemoryCard
        memory={{ ...mockMemory, state: 'active' }}
        showActions={true}
        showMetadata={true}
      />
      <MemoryCard
        memory={{ ...mockMemory, id: 'memory-2', state: 'paused' }}
        showActions={true}
        showMetadata={true}
      />
      <MemoryCard
        memory={{ ...mockMemory, id: 'memory-3', state: 'archived' }}
        showActions={true}
        showMetadata={true}
      />
      <MemoryCard
        memory={{ ...mockMemory, id: 'memory-4', state: 'deleted' }}
        showActions={true}
        showMetadata={true}
      />
    </div>
  ),
  parameters: {
    layout: 'padded',
  },
};

/**
 * Memory cards with different clients
 */
export const DifferentClients: Story = {
  render: () => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-4xl">
      <MemoryCard
        memory={{ ...mockMemory, client: 'chrome' }}
        showActions={true}
        showMetadata={true}
      />
      <MemoryCard
        memory={{ ...mockMemory, id: 'memory-2', client: 'chatgpt' }}
        showActions={true}
        showMetadata={true}
      />
      <MemoryCard
        memory={{ ...mockMemory, id: 'memory-3', client: 'cursor' }}
        showActions={true}
        showMetadata={true}
      />
      <MemoryCard
        memory={{ ...mockMemory, id: 'memory-4', client: 'terminal' }}
        showActions={true}
        showMetadata={true}
      />
    </div>
  ),
  parameters: {
    layout: 'padded',
  },
};

/**
 * Interactive example with working actions
 */
export const Interactive: Story = {
  args: {
    memory: mockMemory,
    showActions: true,
    showMetadata: true,
    compact: false,
  },
  play: async ({ canvasElement, args }) => {
    // This would be used for interaction testing
    // const canvas = within(canvasElement);
    // await userEvent.click(canvas.getByRole('button'));
  },
};
