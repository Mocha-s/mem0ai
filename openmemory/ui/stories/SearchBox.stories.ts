import type { Meta, StoryObj } from '@storybook/react';
import { fn } from '@storybook/test';
import { SearchBox } from '@/components/mem0/SearchBox';
import type { SearchFilters } from '@/components/mem0/SearchBox';

const meta: Meta<typeof SearchBox> = {
  title: 'Mem0/SearchBox',
  component: SearchBox,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: 'An advanced search component with filters, debouncing, and real-time search capabilities.',
      },
    },
  },
  tags: ['autodocs'],
  argTypes: {
    onSearch: {
      description: 'Callback function when search is performed',
      action: 'search',
    },
    onClear: {
      description: 'Callback function when search is cleared',
      action: 'clear',
    },
    placeholder: {
      description: 'Placeholder text for the search input',
      control: { type: 'text' },
    },
    defaultQuery: {
      description: 'Default search query',
      control: { type: 'text' },
    },
    showAdvancedFilters: {
      description: 'Whether to show advanced filter options',
      control: { type: 'boolean' },
    },
    debounceMs: {
      description: 'Debounce delay in milliseconds',
      control: { type: 'number', min: 0, max: 2000, step: 100 },
    },
    availableCategories: {
      description: 'Available category options',
      control: { type: 'object' },
    },
    availableClients: {
      description: 'Available client options',
      control: { type: 'object' },
    },
    availableUsers: {
      description: 'Available user options',
      control: { type: 'object' },
    },
    availableMemoryTypes: {
      description: 'Available memory type options',
      control: { type: 'object' },
    },
  },
  args: {
    onSearch: fn(),
    onClear: fn(),
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Default search box with all features enabled
 */
export const Default: Story = {
  args: {
    placeholder: 'Search memories...',
    showAdvancedFilters: true,
    debounceMs: 300,
    availableCategories: ['personal', 'work', 'health', 'finance', 'travel', 'education'],
    availableClients: ['chrome', 'chatgpt', 'cursor', 'terminal', 'api'],
    availableUsers: ['user-1', 'user-2', 'user-3'],
    availableMemoryTypes: ['episodic', 'semantic', 'procedural'],
  },
};

/**
 * Search box with default query
 */
export const WithDefaultQuery: Story = {
  args: {
    ...Default.args,
    defaultQuery: 'machine learning',
  },
};

/**
 * Search box with default filters
 */
export const WithDefaultFilters: Story = {
  args: {
    ...Default.args,
    defaultFilters: {
      categories: ['work', 'ai'],
      sources: ['openmemory'],
      clients: ['chrome'],
    },
  },
};

/**
 * Simple search box without advanced filters
 */
export const Simple: Story = {
  args: {
    placeholder: 'Simple search...',
    showAdvancedFilters: false,
    debounceMs: 300,
  },
};

/**
 * Search box with custom categories
 */
export const CustomCategories: Story = {
  args: {
    ...Default.args,
    availableCategories: ['research', 'meetings', 'ideas', 'tasks', 'notes'],
    availableClients: ['vscode', 'notion', 'slack', 'email'],
    availableMemoryTypes: ['short-term', 'long-term', 'working'],
  },
};

/**
 * Search box with fast debounce
 */
export const FastDebounce: Story = {
  args: {
    ...Default.args,
    debounceMs: 100,
  },
};

/**
 * Search box with slow debounce
 */
export const SlowDebounce: Story = {
  args: {
    ...Default.args,
    debounceMs: 1000,
  },
};

/**
 * Search box with many categories
 */
export const ManyCategories: Story = {
  args: {
    ...Default.args,
    availableCategories: [
      'personal', 'work', 'health', 'finance', 'travel', 'education',
      'research', 'meetings', 'ideas', 'tasks', 'notes', 'projects',
      'goals', 'habits', 'learning', 'entertainment', 'shopping',
      'family', 'friends', 'hobbies', 'sports', 'technology'
    ],
  },
};

/**
 * Interactive search example
 */
export const Interactive: Story = {
  render: (args) => {
    const handleSearch = (query: string, filters: SearchFilters) => {
      console.log('Search performed:', { query, filters });
      args.onSearch?.(query, filters);
    };

    const handleClear = () => {
      console.log('Search cleared');
      args.onClear?.();
    };

    return (
      <div className="w-full max-w-2xl space-y-4">
        <SearchBox
          {...args}
          onSearch={handleSearch}
          onClear={handleClear}
        />
        <div className="text-sm text-muted-foreground">
          <p>Try searching and using filters. Check the console for search events.</p>
        </div>
      </div>
    );
  },
  args: {
    ...Default.args,
  },
  parameters: {
    layout: 'padded',
  },
};

/**
 * Different sizes demonstration
 */
export const DifferentSizes: Story = {
  render: () => (
    <div className="space-y-6 w-full">
      <div className="w-full max-w-sm">
        <h3 className="text-sm font-medium mb-2">Small (max-w-sm)</h3>
        <SearchBox
          placeholder="Small search..."
          showAdvancedFilters={true}
          availableCategories={['personal', 'work']}
          onSearch={fn()}
        />
      </div>
      <div className="w-full max-w-md">
        <h3 className="text-sm font-medium mb-2">Medium (max-w-md)</h3>
        <SearchBox
          placeholder="Medium search..."
          showAdvancedFilters={true}
          availableCategories={['personal', 'work', 'health']}
          onSearch={fn()}
        />
      </div>
      <div className="w-full max-w-2xl">
        <h3 className="text-sm font-medium mb-2">Large (max-w-2xl)</h3>
        <SearchBox
          placeholder="Large search..."
          showAdvancedFilters={true}
          availableCategories={['personal', 'work', 'health', 'finance', 'travel']}
          onSearch={fn()}
        />
      </div>
    </div>
  ),
  parameters: {
    layout: 'padded',
  },
};
