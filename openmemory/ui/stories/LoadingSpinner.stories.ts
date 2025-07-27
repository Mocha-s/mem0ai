import type { Meta, StoryObj } from '@storybook/react';
import { 
  LoadingSpinner, 
  MemoryLoadingSpinner, 
  DatabaseLoadingSpinner, 
  SearchLoadingSpinner, 
  RefreshLoadingSpinner 
} from '@/components/common/LoadingSpinner';

const meta: Meta<typeof LoadingSpinner> = {
  title: 'Common/LoadingSpinner',
  component: LoadingSpinner,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: 'A versatile loading spinner component with multiple variants and sizes.',
      },
    },
  },
  tags: ['autodocs'],
  argTypes: {
    size: {
      description: 'Size of the spinner',
      control: { type: 'select' },
      options: ['sm', 'md', 'lg', 'xl'],
    },
    variant: {
      description: 'Visual variant of the spinner',
      control: { type: 'select' },
      options: ['default', 'brain', 'database', 'zap', 'refresh'],
    },
    text: {
      description: 'Optional text to display below the spinner',
      control: { type: 'text' },
    },
    fullScreen: {
      description: 'Whether to display as a full-screen overlay',
      control: { type: 'boolean' },
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
 * Default loading spinner
 */
export const Default: Story = {
  args: {
    size: 'md',
    variant: 'default',
  },
};

/**
 * Loading spinner with text
 */
export const WithText: Story = {
  args: {
    size: 'md',
    variant: 'default',
    text: 'Loading...',
  },
};

/**
 * Small spinner
 */
export const Small: Story = {
  args: {
    size: 'sm',
    variant: 'default',
    text: 'Loading',
  },
};

/**
 * Large spinner
 */
export const Large: Story = {
  args: {
    size: 'lg',
    variant: 'default',
    text: 'Please wait...',
  },
};

/**
 * Extra large spinner
 */
export const ExtraLarge: Story = {
  args: {
    size: 'xl',
    variant: 'default',
    text: 'Loading application...',
  },
};

/**
 * Brain variant (for memory operations)
 */
export const Brain: Story = {
  args: {
    size: 'md',
    variant: 'brain',
    text: 'Processing memories...',
  },
};

/**
 * Database variant (for data operations)
 */
export const Database: Story = {
  args: {
    size: 'md',
    variant: 'database',
    text: 'Connecting to database...',
  },
};

/**
 * Zap variant (for fast operations)
 */
export const Zap: Story = {
  args: {
    size: 'md',
    variant: 'zap',
    text: 'Processing...',
  },
};

/**
 * Refresh variant (for refresh operations)
 */
export const Refresh: Story = {
  args: {
    size: 'md',
    variant: 'refresh',
    text: 'Refreshing data...',
  },
};

/**
 * Full screen loading overlay
 */
export const FullScreen: Story = {
  args: {
    size: 'lg',
    variant: 'default',
    text: 'Loading application...',
    fullScreen: true,
  },
  parameters: {
    layout: 'fullscreen',
  },
};

/**
 * All sizes comparison
 */
export const AllSizes: Story = {
  render: () => (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-8 items-center">
      <div className="text-center space-y-2">
        <LoadingSpinner size="sm" />
        <p className="text-sm text-muted-foreground">Small</p>
      </div>
      <div className="text-center space-y-2">
        <LoadingSpinner size="md" />
        <p className="text-sm text-muted-foreground">Medium</p>
      </div>
      <div className="text-center space-y-2">
        <LoadingSpinner size="lg" />
        <p className="text-sm text-muted-foreground">Large</p>
      </div>
      <div className="text-center space-y-2">
        <LoadingSpinner size="xl" />
        <p className="text-sm text-muted-foreground">Extra Large</p>
      </div>
    </div>
  ),
};

/**
 * All variants comparison
 */
export const AllVariants: Story = {
  render: () => (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-8 items-center">
      <div className="text-center space-y-2">
        <LoadingSpinner variant="default" size="md" />
        <p className="text-sm text-muted-foreground">Default</p>
      </div>
      <div className="text-center space-y-2">
        <LoadingSpinner variant="brain" size="md" />
        <p className="text-sm text-muted-foreground">Brain</p>
      </div>
      <div className="text-center space-y-2">
        <LoadingSpinner variant="database" size="md" />
        <p className="text-sm text-muted-foreground">Database</p>
      </div>
      <div className="text-center space-y-2">
        <LoadingSpinner variant="zap" size="md" />
        <p className="text-sm text-muted-foreground">Zap</p>
      </div>
      <div className="text-center space-y-2">
        <LoadingSpinner variant="refresh" size="md" />
        <p className="text-sm text-muted-foreground">Refresh</p>
      </div>
    </div>
  ),
};

/**
 * Specialized loading spinners
 */
export const SpecializedSpinners: Story = {
  render: () => (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      <div className="text-center space-y-4">
        <MemoryLoadingSpinner size="md" />
        <p className="text-sm text-muted-foreground">Memory Loading</p>
      </div>
      <div className="text-center space-y-4">
        <DatabaseLoadingSpinner size="md" />
        <p className="text-sm text-muted-foreground">Database Loading</p>
      </div>
      <div className="text-center space-y-4">
        <SearchLoadingSpinner size="md" />
        <p className="text-sm text-muted-foreground">Search Loading</p>
      </div>
      <div className="text-center space-y-4">
        <RefreshLoadingSpinner size="md" />
        <p className="text-sm text-muted-foreground">Refresh Loading</p>
      </div>
    </div>
  ),
};

/**
 * Loading states in context
 */
export const InContext: Story = {
  render: () => (
    <div className="space-y-8 w-full max-w-2xl">
      <div className="border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Memory Card Loading</h3>
        <div className="flex items-center justify-center h-32 bg-muted rounded-md">
          <MemoryLoadingSpinner size="md" />
        </div>
      </div>
      
      <div className="border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Search Results Loading</h3>
        <div className="flex items-center justify-center h-24 bg-muted rounded-md">
          <SearchLoadingSpinner size="sm" />
        </div>
      </div>
      
      <div className="border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Database Connection</h3>
        <div className="flex items-center justify-center h-20 bg-muted rounded-md">
          <DatabaseLoadingSpinner size="sm" />
        </div>
      </div>
    </div>
  ),
  parameters: {
    layout: 'padded',
  },
};
