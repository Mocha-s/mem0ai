// Component Showcase - 组件展示页面
import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';

// Import our custom components
import { MemoryCard, SearchBox, MemoryList, SourceSwitcher } from '@/components/mem0';
import { LoadingSpinner, ErrorBoundary, EmptyState } from '@/components/common';

// Mock data
const mockMemory = {
  id: 'memory-1',
  content: 'This is a sample memory content that demonstrates how the MemoryCard component displays memory information with various metadata and actions.',
  created_at: '2024-01-15T10:30:00Z',
  updated_at: '2024-01-15T11:00:00Z',
  categories: ['personal', 'work', 'important'],
  metadata: { source: 'test', confidence: 0.95 },
  client: 'chrome',
  app_name: 'openmemory',
  state: 'active',
  user_id: 'user-123',
  score: 0.87,
};

const mockMemories = Array.from({ length: 5 }, (_, i) => ({
  ...mockMemory,
  id: `memory-${i + 1}`,
  content: `Sample memory content ${i + 1}. This demonstrates different memory entries with varying content lengths and metadata.`,
  categories: i % 2 === 0 ? ['personal'] : ['work', 'ai'],
  score: 0.8 + (i * 0.05),
}));

const mockFeatureFlags = {
  enableMem0: true,
  enableOpenMemory: true,
  defaultSource: 'openmemory' as const,
  enableAutoFallback: true,
  enableCaching: false,
  enableTelemetry: false,
};

export const ComponentShowcase: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchFilters, setSearchFilters] = useState({});
  const [currentSource, setCurrentSource] = useState<'openmemory' | 'mem0'>('openmemory');
  const [featureFlags, setFeatureFlags] = useState(mockFeatureFlags);

  const handleSearch = (query: string, filters: any) => {
    setSearchQuery(query);
    setSearchFilters(filters);
    console.log('Search:', { query, filters });
  };

  const handleMemoryAction = (action: string, id: string) => {
    console.log(`${action} memory:`, id);
  };

  return (
    <div className="container mx-auto p-6 space-y-8">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold">Component Showcase</h1>
        <p className="text-muted-foreground">
          Demonstration of all custom components in the Mem0 integration
        </p>
      </div>

      <Tabs defaultValue="memory-components" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="memory-components">Memory Components</TabsTrigger>
          <TabsTrigger value="common-components">Common Components</TabsTrigger>
          <TabsTrigger value="ui-components">UI Components</TabsTrigger>
          <TabsTrigger value="error-states">Error States</TabsTrigger>
        </TabsList>

        {/* Memory Components */}
        <TabsContent value="memory-components" className="space-y-6">
          {/* MemoryCard */}
          <Card>
            <CardHeader>
              <CardTitle>MemoryCard Component</CardTitle>
              <CardDescription>
                Displays individual memory items with metadata, actions, and various display modes.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Badge variant="outline" className="mb-2">Default Mode</Badge>
                  <MemoryCard
                    memory={mockMemory}
                    onEdit={(id) => handleMemoryAction('edit', id)}
                    onDelete={(id) => handleMemoryAction('delete', id)}
                    onView={(id) => handleMemoryAction('view', id)}
                  />
                </div>
                <div>
                  <Badge variant="outline" className="mb-2">Compact Mode</Badge>
                  <MemoryCard
                    memory={mockMemory}
                    compact={true}
                    onEdit={(id) => handleMemoryAction('edit', id)}
                    onDelete={(id) => handleMemoryAction('delete', id)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* SearchBox */}
          <Card>
            <CardHeader>
              <CardTitle>SearchBox Component</CardTitle>
              <CardDescription>
                Advanced search with filters, debouncing, and real-time suggestions.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <SearchBox
                onSearch={handleSearch}
                placeholder="Search memories..."
                showAdvancedFilters={true}
                availableCategories={['personal', 'work', 'health', 'finance', 'ai']}
                availableClients={['chrome', 'chatgpt', 'cursor', 'terminal']}
              />
              {searchQuery && (
                <div className="mt-4 p-3 bg-muted rounded-md">
                  <p className="text-sm">
                    <strong>Search Query:</strong> {searchQuery}
                  </p>
                  <p className="text-sm">
                    <strong>Filters:</strong> {JSON.stringify(searchFilters, null, 2)}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* MemoryList */}
          <Card>
            <CardHeader>
              <CardTitle>MemoryList Component</CardTitle>
              <CardDescription>
                Displays multiple memories with sorting, pagination, and batch operations.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <MemoryList
                memories={mockMemories}
                onEdit={(id) => handleMemoryAction('edit', id)}
                onDelete={(id) => handleMemoryAction('delete', id)}
                onBatchDelete={(ids) => console.log('Batch delete:', ids)}
                onView={(id) => handleMemoryAction('view', id)}
                showBatchActions={true}
              />
            </CardContent>
          </Card>

          {/* SourceSwitcher */}
          <Card>
            <CardHeader>
              <CardTitle>SourceSwitcher Component</CardTitle>
              <CardDescription>
                Switch between OpenMemory and Mem0 APIs with feature flag controls.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <SourceSwitcher
                currentSource={currentSource}
                featureFlags={featureFlags}
                onUpdateFlags={(flags) => setFeatureFlags({ ...featureFlags, ...flags })}
                onSwitchSource={setCurrentSource}
                isSourceAvailable={(source) => source === 'openmemory' || featureFlags.enableMem0}
                showAdvancedSettings={true}
              />
              <div className="mt-4 p-3 bg-muted rounded-md">
                <p className="text-sm">
                  <strong>Current Source:</strong> {currentSource}
                </p>
                <p className="text-sm">
                  <strong>Feature Flags:</strong> {JSON.stringify(featureFlags, null, 2)}
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Common Components */}
        <TabsContent value="common-components" className="space-y-6">
          {/* LoadingSpinner */}
          <Card>
            <CardHeader>
              <CardTitle>LoadingSpinner Component</CardTitle>
              <CardDescription>
                Various loading states with different sizes and variants.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center space-y-2">
                  <Badge variant="outline">Default</Badge>
                  <LoadingSpinner size="md" />
                </div>
                <div className="text-center space-y-2">
                  <Badge variant="outline">Brain</Badge>
                  <LoadingSpinner size="md" variant="brain" />
                </div>
                <div className="text-center space-y-2">
                  <Badge variant="outline">Database</Badge>
                  <LoadingSpinner size="md" variant="database" />
                </div>
                <div className="text-center space-y-2">
                  <Badge variant="outline">With Text</Badge>
                  <LoadingSpinner size="md" text="Loading..." />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* EmptyState */}
          <Card>
            <CardHeader>
              <CardTitle>EmptyState Component</CardTitle>
              <CardDescription>
                Different empty states for various scenarios.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <Badge variant="outline" className="mb-4">Memories Empty State</Badge>
                <EmptyState
                  variant="memories"
                  size="sm"
                  actions={[
                    {
                      label: 'Create Memory',
                      onClick: () => console.log('Create memory'),
                      variant: 'default',
                    },
                  ]}
                />
              </div>
              <Separator />
              <div>
                <Badge variant="outline" className="mb-4">Search Empty State</Badge>
                <EmptyState
                  variant="search"
                  size="sm"
                  actions={[
                    {
                      label: 'Clear Filters',
                      onClick: () => console.log('Clear filters'),
                      variant: 'outline',
                    },
                  ]}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* UI Components */}
        <TabsContent value="ui-components" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Shadcn/ui Components</CardTitle>
              <CardDescription>
                Showcase of the base UI components from shadcn/ui library.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                All components are built on top of the excellent shadcn/ui component library,
                which provides a solid foundation of accessible and customizable UI components.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Badge>Button</Badge>
                <Badge>Card</Badge>
                <Badge>Input</Badge>
                <Badge>Select</Badge>
                <Badge>Checkbox</Badge>
                <Badge>Badge</Badge>
                <Badge>Popover</Badge>
                <Badge>Tooltip</Badge>
                <Badge>Alert</Badge>
                <Badge>Skeleton</Badge>
                <Badge>And many more...</Badge>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Error States */}
        <TabsContent value="error-states" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Error Boundary</CardTitle>
              <CardDescription>
                Error boundary component for catching and displaying React errors.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ErrorBoundary
                showDetails={true}
                showReportButton={true}
                onError={(error, errorInfo) => {
                  console.log('Error caught:', error, errorInfo);
                }}
              >
                <div className="p-4 border rounded-md">
                  <p>This content is wrapped in an ErrorBoundary.</p>
                  <Button
                    onClick={() => {
                      throw new Error('Test error for demonstration');
                    }}
                    variant="destructive"
                    size="sm"
                    className="mt-2"
                  >
                    Trigger Error
                  </Button>
                </div>
              </ErrorBoundary>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Error Empty State</CardTitle>
              <CardDescription>
                Empty state component for error scenarios.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EmptyState
                variant="error"
                size="sm"
                actions={[
                  {
                    label: 'Try Again',
                    onClick: () => console.log('Retry'),
                    variant: 'default',
                  },
                ]}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ComponentShowcase;
