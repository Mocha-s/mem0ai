// MemoryList Component - 记忆列表组件
import React, { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { MemoryCard } from './MemoryCard';
import { 
  Grid, 
  List, 
  ChevronUp, 
  ChevronDown, 
  Trash2, 
  Edit, 
  RefreshCw,
  AlertCircle,
  CheckSquare,
  Square
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { UnifiedMemory } from '@/lib/types/unified';

export interface MemoryListProps {
  memories: UnifiedMemory[];
  loading?: boolean;
  error?: string | null;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
  onBatchDelete?: (ids: string[]) => void;
  onView?: (id: string) => void;
  onRefresh?: () => void;
  className?: string;
  emptyMessage?: string;
  showBatchActions?: boolean;
  defaultViewMode?: 'grid' | 'list';
  defaultSortBy?: 'created_at' | 'updated_at' | 'content' | 'score';
  defaultSortOrder?: 'asc' | 'desc';
  itemsPerPage?: number;
}

type SortField = 'created_at' | 'updated_at' | 'content' | 'score';
type SortOrder = 'asc' | 'desc';
type ViewMode = 'grid' | 'list';

export const MemoryList: React.FC<MemoryListProps> = ({
  memories,
  loading = false,
  error = null,
  onEdit,
  onDelete,
  onBatchDelete,
  onView,
  onRefresh,
  className,
  emptyMessage = "No memories found",
  showBatchActions = true,
  defaultViewMode = 'grid',
  defaultSortBy = 'created_at',
  defaultSortOrder = 'desc',
  itemsPerPage = 20,
}) => {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<ViewMode>(defaultViewMode);
  const [sortBy, setSortBy] = useState<SortField>(defaultSortBy);
  const [sortOrder, setSortOrder] = useState<SortOrder>(defaultSortOrder);
  const [currentPage, setCurrentPage] = useState(1);

  // Sort memories
  const sortedMemories = useMemo(() => {
    const sorted = [...memories].sort((a, b) => {
      let aValue: any, bValue: any;

      switch (sortBy) {
        case 'created_at':
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
          break;
        case 'updated_at':
          aValue = a.updated_at ? new Date(a.updated_at).getTime() : 0;
          bValue = b.updated_at ? new Date(b.updated_at).getTime() : 0;
          break;
        case 'content':
          aValue = a.content.toLowerCase();
          bValue = b.content.toLowerCase();
          break;
        case 'score':
          aValue = a.score || 0;
          bValue = b.score || 0;
          break;
        default:
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
      }

      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    return sorted;
  }, [memories, sortBy, sortOrder]);

  // Paginate memories
  const paginatedMemories = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return sortedMemories.slice(startIndex, endIndex);
  }, [sortedMemories, currentPage, itemsPerPage]);

  const totalPages = Math.ceil(sortedMemories.length / itemsPerPage);

  // Selection handlers
  const handleSelectAll = () => {
    if (selectedIds.size === paginatedMemories.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(paginatedMemories.map(m => m.id)));
    }
  };

  const handleSelectMemory = (id: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const handleBatchDelete = () => {
    if (selectedIds.size > 0 && onBatchDelete) {
      onBatchDelete(Array.from(selectedIds));
      setSelectedIds(new Set());
    }
  };

  // Loading skeleton
  if (loading) {
    return (
      <div className={cn("space-y-4", className)}>
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-32" />
          <div className="flex space-x-2">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-8 w-24" />
          </div>
        </div>
        <div className={cn(
          "grid gap-4",
          viewMode === 'grid' 
            ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-3" 
            : "grid-cols-1"
        )}>
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-48 w-full" />
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <Alert variant="destructive" className={className}>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          {error}
          {onRefresh && (
            <Button variant="outline" size="sm" className="ml-2" onClick={onRefresh}>
              <RefreshCw className="h-4 w-4 mr-1" />
              Retry
            </Button>
          )}
        </AlertDescription>
      </Alert>
    );
  }

  // Empty state
  if (memories.length === 0) {
    return (
      <div className={cn("text-center py-12", className)}>
        <div className="text-muted-foreground mb-4">
          <div className="text-4xl mb-2">🧠</div>
          <p>{emptyMessage}</p>
        </div>
        {onRefresh && (
          <Button variant="outline" onClick={onRefresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="text-sm text-muted-foreground">
            {memories.length} memories
          </div>
          
          {showBatchActions && selectedIds.size > 0 && (
            <div className="flex items-center space-x-2">
              <Badge variant="secondary">
                {selectedIds.size} selected
              </Badge>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleBatchDelete}
              >
                <Trash2 className="h-4 w-4 mr-1" />
                Delete Selected
              </Button>
            </div>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {/* Sort Controls */}
          <Select value={sortBy} onValueChange={(value: SortField) => setSortBy(value)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="created_at">Created</SelectItem>
              <SelectItem value="updated_at">Updated</SelectItem>
              <SelectItem value="content">Content</SelectItem>
              <SelectItem value="score">Score</SelectItem>
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
          >
            {sortOrder === 'asc' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>

          {/* View Mode Toggle */}
          <div className="flex border rounded-md">
            <Button
              variant={viewMode === 'grid' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('grid')}
              className="rounded-r-none"
            >
              <Grid className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('list')}
              className="rounded-l-none"
            >
              <List className="h-4 w-4" />
            </Button>
          </div>

          {onRefresh && (
            <Button variant="outline" size="sm" onClick={onRefresh}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Batch Selection Header */}
      {showBatchActions && (
        <div className="flex items-center space-x-2 py-2 border-b">
          <Checkbox
            checked={selectedIds.size === paginatedMemories.length && paginatedMemories.length > 0}
            onCheckedChange={handleSelectAll}
          />
          <span className="text-sm text-muted-foreground">
            Select all on this page
          </span>
        </div>
      )}

      {/* Memory Grid/List */}
      <div className={cn(
        "grid gap-4",
        viewMode === 'grid' 
          ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-3" 
          : "grid-cols-1"
      )}>
        {paginatedMemories.map((memory) => (
          <div key={memory.id} className="relative">
            {showBatchActions && (
              <div className="absolute top-2 left-2 z-10">
                <Checkbox
                  checked={selectedIds.has(memory.id)}
                  onCheckedChange={() => handleSelectMemory(memory.id)}
                  className="bg-background border-2"
                />
              </div>
            )}
            <MemoryCard
              memory={memory}
              onEdit={onEdit}
              onDelete={onDelete}
              onView={onView}
              compact={viewMode === 'list'}
              className={cn(
                showBatchActions && "pl-8",
                selectedIds.has(memory.id) && "ring-2 ring-primary"
              )}
            />
          </div>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
          >
            Previous
          </Button>
          
          <div className="flex items-center space-x-1">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const page = i + 1;
              return (
                <Button
                  key={page}
                  variant={currentPage === page ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setCurrentPage(page)}
                >
                  {page}
                </Button>
              );
            })}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
};

export default MemoryList;
