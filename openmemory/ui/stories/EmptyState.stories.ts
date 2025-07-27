import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { 
  EmptyState, 
  MemoriesEmptyState, 
  SearchEmptyState, 
  ErrorEmptyState, 
  LoadingEmptyState 
} from '@/components/common/EmptyState';
import { Brain, Search, AlertCircle, Plus, RefreshCw } from 'lucide-react';

const meta: Meta<typeof EmptyState> = {
  title: 'Common/EmptyState',
  component: EmptyState,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: 'A flexible empty state component for displaying various no-content scenarios.',
      },
    },
  },
  tags: ['autodocs'],
  argTypes: {
    variant: {
      description: 'Predefined variant of the empty state',
      control: { type: 'select' },
      options: ['memories', 'search', 'error', 'loading', 'custom'],
    },
    title: {
      description: 'Title text to display',
      control: { type: 'text' },
    },
    description: {
      description: 'Description text to display',
      control: { type: 'text' },
    },
    size: {
      description: 'Size of the empty state',
      control: { type: 'select' },
      options: ['sm', 'md', 'lg'],
    },
    icon: {
      description: 'Custom icon to display',
      control: { type: 'object' },
    },
    actions: {
      description: 'Array of action buttons',
      control: { type: 'object' },
    },
    className: {
      description: 'Additional CSS classes',
      control: { type: 'text' },
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default memories empty state
 */
export const Memories: Story = {
  args: {
    variant: 'memories',
    size: 'md',
    actions: [
      {
        label: 'Create Memory',
        onClick: fn(),
        variant: 'default',
        icon: <Plus className="h-4 w-4" />,
      },
      {
        label: 'Refresh',
        onClick: fn(),
        variant: 'outline',
        icon: <RefreshCw className="h-4 w-4" />,
      },
    ],
  },
};

/**
 * Search results empty state
 */
export const Search: Story = {
  args: {
    variant: 'search',
    size: 'md',
    actions: [
      {
        label: 'Clear Filters',
        onClick: fn(),
        variant: 'outline',
        icon: <RefreshCw className="h-4 w-4" />,
      },
    ],
  },
};

/**
 * Error empty state
 */
export const Error: Story = {
  args: {
    variant: 'error',
    size: 'md',
    actions: [
      {
        label: 'Try Again',
        onClick: fn(),
        variant: 'default',
        icon: <RefreshCw className="h-4 w-4" />,
      },
    ],
  },
};

/**
 * Loading empty state
 */
export const Loading: Story = {
  args: {
    variant: 'loading',
    size: 'md',
  },
};

/**
 * Custom empty state
 */
export const Custom: Story = {
  args: {
    variant: 'custom',
    title: 'Custom Empty State',
    description: 'This is a custom empty state with custom content and actions.',
    icon: <Brain className="h-12 w-12 text-muted-foreground" />,
    size: 'md',
    actions: [
      {
        label: 'Custom Action',
        onClick: fn(),
        variant: 'default',
      },
    ],
  },
};

/**
 * Small size
 */
export const Small: Story = {
  args: {
    variant: 'memories',
    size: 'sm',
    actions: [
      {
        label: 'Create',
        onClick: fn(),
        variant: 'default',
      },
    ],
  },
};

/**
 * Large size
 */
export const Large: Story = {
  args: {
    variant: 'memories',
    size: 'lg',
    actions: [
      {
        label: 'Create Memory',
        onClick: fn(),
        variant: 'default',
        icon: <Plus className="h-4 w-4" />,
      },
      {
        label: 'Import Data',
        onClick: fn(),
        variant: 'outline',
      },
    ],
  },
};

/**
 * Without actions
 */
export const NoActions: Story = {
  args: {
    variant: 'memories',
    size: 'md',
    actions: [],
  },
};

/**
 * Custom title and description
 */
export const CustomContent: Story = {
  args: {
    variant: 'custom',
    title: 'No Projects Found',
    description: 'You haven\'t created any projects yet. Projects help you organize your memories and collaborate with others.',
    icon: <Search className="h-12 w-12 text-muted-foreground" />,
    size: 'md',
    actions: [
      {
        label: 'Create Project',
        onClick: fn(),
        variant: 'default',
      },
      {
        label: 'Learn More',
        onClick: fn(),
        variant: 'outline',
      },
    ],
  },
};

/**
 * All variants comparison
 */
export const AllVariants: Story = {
  render: () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 w-full">
      <div className="border rounded-lg p-4">
        <h3 className="text-sm font-medium mb-4 text-center">Memories</h3>
        <EmptyState
          variant="memories"
          size="sm"
          actions={[
            {
              label: 'Create',
              onClick: fn(),
              variant: 'default',
            },
          ]}
        />
      </div>
      
      <div className="border rounded-lg p-4">
        <h3 className="text-sm font-medium mb-4 text-center">Search</h3>
        <EmptyState
          variant="search"
          size="sm"
          actions={[
            {
              label: 'Clear',
              onClick: fn(),
              variant: 'outline',
            },
          ]}
        />
      </div>
      
      <div className="border rounded-lg p-4">
        <h3 className="text-sm font-medium mb-4 text-center">Error</h3>
        <EmptyState
          variant="error"
          size="sm"
          actions={[
            {
              label: 'Retry',
              onClick: fn(),
              variant: 'default',
            },
          ]}
        />
      </div>
      
      <div className="border rounded-lg p-4">
        <h3 className="text-sm font-medium mb-4 text-center">Loading</h3>
        <EmptyState
          variant="loading"
          size="sm"
        />
      </div>
      
      <div className="border rounded-lg p-4">
        <h3 className="text-sm font-medium mb-4 text-center">Custom</h3>
        <EmptyState
          variant="custom"
          title="Custom"
          description="Custom empty state"
          size="sm"
          actions={[
            {
              label: 'Action',
              onClick: fn(),
              variant: 'default',
            },
          ]}
        />
      </div>
    </div>
  ),
  parameters: {
    layout: 'padded',
  },
};

/**
 * Specialized empty states
 */
export const SpecializedStates: Story = {
  render: () => (
    <div className="space-y-8 w-full max-w-4xl">
      <div className="border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Memories Empty State</h3>
        <MemoriesEmptyState
          onCreateMemory={fn()}
          onRefresh={fn()}
          size="md"
        />
      </div>
      
      <div className="border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Search Empty State</h3>
        <SearchEmptyState
          searchQuery="machine learning"
          onClearFilters={fn()}
          size="md"
        />
      </div>
      
      <div className="border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Error Empty State</h3>
        <ErrorEmptyState
          error="Failed to connect to the server. Please check your internet connection."
          onRetry={fn()}
          size="md"
        />
      </div>
      
      <div className="border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Loading Empty State</h3>
        <LoadingEmptyState
          loadingText="Loading your memories..."
          size="md"
        />
      </div>
    </div>
  ),
  parameters: {
    layout: 'padded',
  },
};

/**
 * Interactive example
 */
export const Interactive: Story = {
  render: (args) => {
    const handleAction = (actionName: string) => {
      console.log(`Action triggered: ${actionName}`);
      args.actions?.[0]?.onClick?.();
    };

    return (
      <div className="w-full max-w-2xl space-y-4">
        <EmptyState
          {...args}
          actions={[
            {
              label: 'Primary Action',
              onClick: () => handleAction('primary'),
              variant: 'default',
              icon: <Plus className="h-4 w-4" />,
            },
            {
              label: 'Secondary Action',
              onClick: () => handleAction('secondary'),
              variant: 'outline',
              icon: <RefreshCw className="h-4 w-4" />,
            },
          ]}
        />
        <div className="text-sm text-muted-foreground text-center">
          <p>Click the action buttons to see console output.</p>
        </div>
      </div>
    );
  },
  args: {
    variant: 'memories',
    size: 'md',
  },
  parameters: {
    layout: 'padded',
  },
};
