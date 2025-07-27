// SearchBox Component - 高级搜索组件
import React, { useState, useCallback, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Search, Filter, X, Calendar, User, Tag, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { UnifiedSearchOptions } from '@/lib/types/unified';

export interface SearchFilters {
  categories?: string[];
  sources?: ('openmemory' | 'mem0')[];
  clients?: string[];
  dateRange?: {
    from?: string;
    to?: string;
  };
  userIds?: string[];
  minScore?: number;
  memoryTypes?: string[];
}

export interface SearchBoxProps {
  onSearch: (query: string, filters: SearchFilters) => void;
  onClear?: () => void;
  placeholder?: string;
  className?: string;
  defaultQuery?: string;
  defaultFilters?: SearchFilters;
  availableCategories?: string[];
  availableClients?: string[];
  availableUsers?: string[];
  availableMemoryTypes?: string[];
  showAdvancedFilters?: boolean;
  debounceMs?: number;
}

export const SearchBox: React.FC<SearchBoxProps> = ({
  onSearch,
  onClear,
  placeholder = "Search memories...",
  className,
  defaultQuery = "",
  defaultFilters = {},
  availableCategories = ['personal', 'work', 'health', 'finance', 'travel', 'education'],
  availableClients = ['chrome', 'chatgpt', 'cursor', 'terminal', 'api'],
  availableUsers = [],
  availableMemoryTypes = ['episodic', 'semantic', 'procedural'],
  showAdvancedFilters = true,
  debounceMs = 300,
}) => {
  const [query, setQuery] = useState(defaultQuery);
  const [filters, setFilters] = useState<SearchFilters>(defaultFilters);
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);

  // Debounced search
  const debouncedSearch = useCallback((searchQuery: string, searchFilters: SearchFilters) => {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    
    const timer = setTimeout(() => {
      onSearch(searchQuery, searchFilters);
    }, debounceMs);
    
    setDebounceTimer(timer);
  }, [onSearch, debounceMs, debounceTimer]);

  // Handle query change
  const handleQueryChange = (value: string) => {
    setQuery(value);
    debouncedSearch(value, filters);
  };

  // Handle filter change
  const handleFilterChange = (newFilters: SearchFilters) => {
    setFilters(newFilters);
    debouncedSearch(query, newFilters);
  };

  // Handle immediate search
  const handleSearch = () => {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    onSearch(query, filters);
  };

  // Handle clear
  const handleClear = () => {
    setQuery("");
    setFilters({});
    onClear?.();
  };

  // Count active filters
  const activeFilterCount = Object.values(filters).filter(value => {
    if (Array.isArray(value)) return value.length > 0;
    if (typeof value === 'object' && value !== null) return Object.keys(value).length > 0;
    return value !== undefined && value !== null;
  }).length;

  // Update filter helper
  const updateFilter = <K extends keyof SearchFilters>(key: K, value: SearchFilters[K]) => {
    handleFilterChange({ ...filters, [key]: value });
  };

  // Toggle array filter item
  const toggleArrayFilter = <K extends keyof SearchFilters>(
    key: K, 
    item: string, 
    currentArray: string[] = []
  ) => {
    const newArray = currentArray.includes(item)
      ? currentArray.filter(i => i !== item)
      : [...currentArray, item];
    updateFilter(key, newArray as SearchFilters[K]);
  };

  useEffect(() => {
    return () => {
      if (debounceTimer) {
        clearTimeout(debounceTimer);
      }
    };
  }, [debounceTimer]);

  return (
    <div className={cn("space-y-2", className)}>
      {/* Main Search Input */}
      <div className="relative flex items-center space-x-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
            placeholder={placeholder}
            className="pl-10 pr-10"
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSearch();
              }
            }}
          />
          {query && (
            <Button
              variant="ghost"
              size="sm"
              className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
              onClick={() => handleQueryChange("")}
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>

        <Button onClick={handleSearch} size="sm">
          <Search className="h-4 w-4" />
        </Button>

        {showAdvancedFilters && (
          <Popover open={isFilterOpen} onOpenChange={setIsFilterOpen}>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm" className="relative">
                <Filter className="h-4 w-4" />
                {activeFilterCount > 0 && (
                  <Badge 
                    variant="destructive" 
                    className="absolute -top-2 -right-2 h-5 w-5 p-0 text-xs"
                  >
                    {activeFilterCount}
                  </Badge>
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-80" align="end">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium">Advanced Filters</h4>
                  <Button variant="ghost" size="sm" onClick={handleClear}>
                    Clear All
                  </Button>
                </div>

                <Separator />

                {/* Sources */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Sources</Label>
                  <div className="flex flex-wrap gap-2">
                    {['openmemory', 'mem0'].map((source) => (
                      <div key={source} className="flex items-center space-x-2">
                        <Checkbox
                          id={`source-${source}`}
                          checked={filters.sources?.includes(source as any) || false}
                          onCheckedChange={(checked) => {
                            if (checked) {
                              toggleArrayFilter('sources', source, filters.sources);
                            } else {
                              toggleArrayFilter('sources', source, filters.sources);
                            }
                          }}
                        />
                        <Label htmlFor={`source-${source}`} className="text-sm">
                          {source === 'openmemory' ? '💾 OpenMemory' : '🧠 Mem0'}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Categories */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Categories</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {availableCategories.map((category) => (
                      <div key={category} className="flex items-center space-x-2">
                        <Checkbox
                          id={`category-${category}`}
                          checked={filters.categories?.includes(category) || false}
                          onCheckedChange={() => {
                            toggleArrayFilter('categories', category, filters.categories);
                          }}
                        />
                        <Label htmlFor={`category-${category}`} className="text-sm">
                          <Tag className="inline h-3 w-3 mr-1" />
                          {category}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Clients */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Clients</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {availableClients.map((client) => (
                      <div key={client} className="flex items-center space-x-2">
                        <Checkbox
                          id={`client-${client}`}
                          checked={filters.clients?.includes(client) || false}
                          onCheckedChange={() => {
                            toggleArrayFilter('clients', client, filters.clients);
                          }}
                        />
                        <Label htmlFor={`client-${client}`} className="text-sm capitalize">
                          {client}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Memory Types */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Memory Types</Label>
                  <div className="space-y-2">
                    {availableMemoryTypes.map((type) => (
                      <div key={type} className="flex items-center space-x-2">
                        <Checkbox
                          id={`type-${type}`}
                          checked={filters.memoryTypes?.includes(type) || false}
                          onCheckedChange={() => {
                            toggleArrayFilter('memoryTypes', type, filters.memoryTypes);
                          }}
                        />
                        <Label htmlFor={`type-${type}`} className="text-sm capitalize">
                          <Zap className="inline h-3 w-3 mr-1" />
                          {type}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>

                <Separator />

                <div className="flex justify-end space-x-2">
                  <Button variant="outline" size="sm" onClick={() => setIsFilterOpen(false)}>
                    Close
                  </Button>
                  <Button size="sm" onClick={() => {
                    handleSearch();
                    setIsFilterOpen(false);
                  }}>
                    Apply Filters
                  </Button>
                </div>
              </div>
            </PopoverContent>
          </Popover>
        )}
      </div>

      {/* Active Filters Display */}
      {activeFilterCount > 0 && (
        <div className="flex flex-wrap gap-1">
          {filters.categories?.map((category) => (
            <Badge key={`cat-${category}`} variant="secondary" className="text-xs">
              <Tag className="mr-1 h-3 w-3" />
              {category}
              <Button
                variant="ghost"
                size="sm"
                className="ml-1 h-3 w-3 p-0"
                onClick={() => toggleArrayFilter('categories', category, filters.categories)}
              >
                <X className="h-2 w-2" />
              </Button>
            </Badge>
          ))}
          {filters.sources?.map((source) => (
            <Badge key={`src-${source}`} variant="outline" className="text-xs">
              {source === 'openmemory' ? '💾' : '🧠'} {source}
              <Button
                variant="ghost"
                size="sm"
                className="ml-1 h-3 w-3 p-0"
                onClick={() => toggleArrayFilter('sources', source, filters.sources)}
              >
                <X className="h-2 w-2" />
              </Button>
            </Badge>
          ))}
          {filters.clients?.map((client) => (
            <Badge key={`cli-${client}`} variant="outline" className="text-xs">
              {client}
              <Button
                variant="ghost"
                size="sm"
                className="ml-1 h-3 w-3 p-0"
                onClick={() => toggleArrayFilter('clients', client, filters.clients)}
              >
                <X className="h-2 w-2" />
              </Button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
};

export default SearchBox;
